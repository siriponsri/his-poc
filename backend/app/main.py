from pathlib import Path
import os
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,FileResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError,OperationalError
from starlette.concurrency import run_in_threadpool
from .db import engine,SessionLocal
from . import model_registry,auth,core,ai,admin,integrations,dr_gateway,assistant_api,admin_ai
from .domains import clinical,erp,operations
from .legacy_import import make_router
app=FastAPI(title='HIS POC Development Prototype',version='0.3.0',docs_url='/api/docs',openapi_url='/api/v2/openapi.json')
for router in [auth.router,operations.router,core.router,ai.router,admin.router,admin_ai.router,clinical.router,erp.router,integrations.router,dr_gateway.router,assistant_api.router,make_router()]:app.include_router(router,prefix='/api/v2')
app.include_router(dr_gateway.browser_router)
@app.exception_handler(IntegrityError)
def integrity_error(request,exc):return JSONResponse(status_code=409,content={'detail':{'code':'CONSTRAINT_CONFLICT','outcome':'not_written'}})
@app.exception_handler(OperationalError)
def database_error(request,exc):return JSONResponse(status_code=503,content={'detail':{'code':'DATABASE_UNAVAILABLE','outcome':'unknown'}})
def persist_security_event(request:Request,status_code:int):
    # FK checks may wait for another request's identity mutation to commit.
    # Keep this synchronous database work off the ASGI event loop so that
    # request can finish its transaction while the denial is being recorded.
    from .models import SecurityEvent,SessionRecord,User
    from .common import text_hash
    from sqlalchemy import select
    with SessionLocal.begin() as db:
        raw=request.cookies.get('his_session');session=db.scalar(select(SessionRecord).where(SessionRecord.token_hash==text_hash(raw))) if raw else None
        user=db.get(User,session.user_id) if session else None
        route=getattr(request.scope.get('route'),'path','unmatched-api-route')
        db.add(SecurityEvent(organization_id=user.organization_id if user else None,facility_id=session.facility_id if session else None,actor_id=user.id if user else None,method=request.method,route_template=route,status_code=status_code,event='request_denied_or_rejected'))
@app.middleware('http')
async def headers(request:Request,call_next):
    response=await call_next(request)
    if request.url.path.startswith(('/api/','/integrations/dr/')) and response.status_code in (401,403,404,409,422,429):
        try:
            await run_in_threadpool(persist_security_event,request,response.status_code)
        except Exception:
            response.headers['X-Security-Event-Persisted']='false'
    response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='same-origin'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'"
    return response
@app.get('/health')
def health():return {'status':'alive','version':'0.3.0','profile':'synthetic_postgresql','provider':os.getenv('HIS_AI_PROVIDER','mock_demo')}
@app.get('/ready')
def ready():
    try:
        with engine.connect() as conn:
            version=conn.scalar(text('select version_num from alembic_version'))
            if version!='0006_team_coordination':return JSONResponse(status_code=503,content={'ready':False,'reason':'MIGRATION_REQUIRED'})
        return {'ready':True,'migration':version}
    except Exception:return JSONResponse(status_code=503,content={'ready':False,'reason':'DATABASE_OR_SCHEMA_UNAVAILABLE'})
@app.get('/{path:path}',include_in_schema=False)
def frontend(path:str):
    if path.startswith(('api/','health','ready','integrations/dr/')):return JSONResponse(status_code=404,content={'detail':{'code':'NOT_FOUND'}})
    root=Path(os.environ.get('WEB_DIST','apps/web/dist')).resolve();candidate=(root/path).resolve()
    if candidate.is_relative_to(root) and candidate.is_file():return FileResponse(candidate)
    if (root/'index.html').is_file():return FileResponse(root/'index.html')
    return JSONResponse(status_code=503,content={'detail':{'code':'FRONTEND_BUILD_REQUIRED','command':'cd apps/web && npm ci && npm run build'}})
