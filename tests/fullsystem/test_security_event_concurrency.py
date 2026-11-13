"""Live ASGI event-loop regression under a real PostgreSQL identity-row lock."""
import json,os,socket,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import httpx,psycopg,pytest
from sqlalchemy import select
from backend.app.db import engine,SessionLocal
from backend.app import models as m
from backend.app.auth import password_hasher
from backend.app.common import uid
from backend.app.domains.operations import pg_url

PASSWORD='SyntheticSecurityConcurrencyOnly-2026!'
EVIDENCE=[]
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def live_server(tmp_path_factory):
 assert engine.dialect.name=='postgresql' and engine.url.database.endswith(('_test','_tests'))
 assert os.environ.get('HIS_TEST_DATABASE_URL')==os.environ.get('DATABASE_URL')
 subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],cwd=ROOT,check=True)
 from backend.app.seed import seed
 with SessionLocal.begin() as db:seed(db,PASSWORD)
 with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
 base=f'http://127.0.0.1:{port}';folder=tmp_path_factory.mktemp('security-event-live')
 with (folder/'uvicorn.txt').open('w',encoding='utf-8') as log:
  process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=dict(os.environ,HIS_ALLOWED_ORIGINS=base,PYTHONUTF8='1'),stdout=log,stderr=log)
  try:
   deadline=time.monotonic()+30
   while time.monotonic()<deadline:
    if process.poll() is not None:pytest.fail('Live Uvicorn exited before readiness')
    try:
     if httpx.get(base+'/health',timeout=1).status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.1)
   else:pytest.fail('Live Uvicorn readiness timeout')
   yield base
  finally:
   process.terminate()
   try:process.wait(timeout=10)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
 output=ROOT/'evidence/fullsystem/windows-20261113/security-event-concurrency-records.json'
 output.write_text(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(),'method':'LIVE_UVICORN_HTTP_POSTGRESQL','records':EVIDENCE},indent=2)+'\n',encoding='utf-8')

def login(base,username):
 client=httpx.Client(base_url=base,timeout=15)
 response=client.post('/api/v2/auth/login',json={'username':username,'password':PASSWORD})
 assert response.status_code==200,response.text
 return client,response.json()['csrf_token']

def test_security_event_fk_wait_does_not_freeze_live_event_loop(live_server):
 client,_csrf=login(live_server,'quality')
 try:
  with psycopg.connect(pg_url(os.environ['DATABASE_URL'])) as held,psycopg.connect(pg_url(os.environ['DATABASE_URL']),autocommit=True) as observer,ThreadPoolExecutor(max_workers=1) as pool:
   held.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',('user-quality',))
   pending=pool.submit(client.get,'/api/v2/admin/users')
   try:
    deadline=time.monotonic()+10;waiting=False
    while time.monotonic()<deadline:
     waiting=observer.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query ILIKE '%INSERT INTO security_events%')").fetchone()[0]
     if waiting:break
     time.sleep(.05)
    assert waiting,'SecurityEvent insert did not reach the controlled FK lock wait'
    assert not pending.done(),'Denial must still be waiting for its atomic security-event insert'
    start=time.monotonic();health=httpx.get(live_server+'/health',timeout=2);latency=time.monotonic()-start
    assert health.status_code==200 and latency<2
   finally:held.rollback()
   denied=pending.result(timeout=10)
   assert denied.status_code==403 and denied.headers.get('x-security-event-persisted')!='false'
  with SessionLocal() as db:
   # Included-router templates omit the /api/v2 mount prefix in this FastAPI runtime.
   events=list(db.scalars(select(m.SecurityEvent).where(m.SecurityEvent.actor_id=='user-quality',m.SecurityEvent.route_template=='/admin/users',m.SecurityEvent.status_code==403)))
   assert len(events)==1 and events[0].method=='GET' and events[0].event=='request_denied_or_rejected'
   assert events[0].organization_id=='org-demo' and events[0].facility_id=='facility-demo'
   EVIDENCE.append({'check':'security_event_fk_lock_event_loop','security_event_id':events[0].id,'route_template':events[0].route_template,'actor_id':'user-quality','held_fk_lock_observed':True,'independent_health_status':health.status_code,'independent_health_seconds':round(latency,3),'denied_status':denied.status_code})
 finally:client.close()

def test_support_staff_audit_allows_quality_and_denies_wrong_role_and_facility(live_server):
 quality,csrf=login(live_server,'quality');registration,_=login(live_server,'registration');nurse,_=login(live_server,'nurse')
 username='other-quality-'+uid();user_id=uid()
 with SessionLocal.begin() as db:
  db.add(m.User(id=user_id,organization_id='org-demo',username=username,display_name='Synthetic other-facility quality',password_hash=password_hasher.hash(PASSWORD),status='active'));db.flush()
  db.add(m.Membership(user_id=user_id,facility_id='facility-second',role='quality'))
 other,_=login(live_server,username)
 try:
  response=quality.post('/api/v2/erp/staff/staff-nurse/credential',json={'version':1,'status':'suspended','reason':'Synthetic audit support regression'},headers={'X-CSRF-Token':csrf,'Idempotency-Key':uid()})
  assert response.status_code==200,response.text
  allowed=quality.get('/api/v2/audit',params={'entity_id':'staff-nurse'})
  assert allowed.status_code==200,allowed.text
  rows=allowed.json()['items'];assert any(row['entity_id']=='staff-nurse' and row['action']=='credential.suspended' for row in rows)
  wrong_role=registration.get('/api/v2/audit',params={'entity_id':'staff-nurse'})
  wrong_scope=other.get('/api/v2/audit',params={'entity_id':'staff-nurse'})
  assert wrong_role.status_code==403 and wrong_scope.status_code in (403,404)
  assert 'credential.suspended' not in wrong_role.text and 'credential.suspended' not in wrong_scope.text
  own=nurse.get('/api/v2/audit',params={'entity_id':'staff-nurse'});assert own.status_code==200
  assert any(row['entity_id']=='staff-nurse' for row in own.json()['items'])
  hidden=nurse.get('/api/v2/audit',params={'entity_id':'staff-quality'});assert hidden.status_code in (403,404)
  quality_other=quality.get('/api/v2/audit',params={'entity_id':'staff-quality'});assert quality_other.status_code==200
  EVIDENCE.append({'check':'support_staff_entity_audit','staff_id':'staff-nurse','audit_ids':[row['id'] for row in rows],'quality_status':allowed.status_code,'wrong_role_status':wrong_role.status_code,'other_facility_status':wrong_scope.status_code,'nurse_own_status':own.status_code,'nurse_other_staff_status':hidden.status_code,'quality_other_staff_status':quality_other.status_code})
 finally:
  quality.close();registration.close();other.close();nurse.close()
