from typing import Literal
from datetime import timedelta
from fastapi import APIRouter,Depends,Header,HTTPException,Query
from pydantic import Field
from sqlalchemy import select,func,text
from .db import get_db
from .auth import *
from .models import *
from .common import *
router=APIRouter(prefix='/admin',tags=['administration'])

@router.get('/overview')
def overview(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    """Persisted administration metadata only; never probe a provider or chart."""
    require_domain(actor,'D34');require(actor,'identity.admin')
    from .models_assistant import AssistantRun,AssistantWatch
    from .assistant_provider import assistant_provider_config
    observed=utcnow()
    statuses=dict(db.execute(select(User.status,func.count()).where(User.organization_id==actor.organization_id).group_by(User.status)).all())
    user_counts={'total':sum(statuses.values()),**{state:statuses.get(state,0) for state in ('active','suspended','disabled')}}
    active,revoked,expired=db.execute(select(
        func.count().filter(SessionRecord.revoked_at.is_(None),SessionRecord.expires_at>observed),
        func.count().filter(SessionRecord.revoked_at.is_not(None)),
        func.count().filter(SessionRecord.revoked_at.is_(None),SessionRecord.expires_at<=observed),
    ).join(User,User.id==SessionRecord.user_id).where(User.organization_id==actor.organization_id)).one()
    denied=db.scalar(select(func.count()).select_from(SecurityEvent).where(
        SecurityEvent.organization_id==actor.organization_id,SecurityEvent.facility_id==actor.facility_id,
        SecurityEvent.created_at>=observed-timedelta(hours=24),SecurityEvent.created_at<=observed,
        SecurityEvent.event=='request_denied_or_rejected',SecurityEvent.status_code.in_((401,403,404,409,422,429)),
    ))
    counts=db.execute(select(
        func.count().filter(AssistantRun.execution_state.in_(('queued','waiting_for_capacity'))),
        func.count().filter(AssistantRun.execution_state=='running'),
        func.count().filter(AssistantRun.execution_state=='succeeded'),
        func.count().filter(AssistantRun.execution_state.in_(('failed','timeout','invalid_output','abstained','interrupted'))),
        func.count().filter(AssistantRun.execution_state=='succeeded',AssistantRun.review_state=='pending'),
    ).where(AssistantRun.organization_id==actor.organization_id,AssistantRun.facility_id==actor.facility_id)).one()
    watches=db.scalar(select(func.count()).select_from(AssistantWatch).where(
        AssistantWatch.organization_id==actor.organization_id,AssistantWatch.facility_id==actor.facility_id,
        AssistantWatch.status=='active',AssistantWatch.expires_at>observed,
    ))
    provider=assistant_provider_config()  # Pure configuration inspection, no HTTP.
    return {
        'scope':{'organization_id':actor.organization_id,'facility_id':actor.facility_id},
        'users':user_counts,'sessions':{'active':active,'revoked':revoked,'expired':expired},
        'security':{'recent_denial_count':denied,'window_hours':24},
        'database':{'reachable':True,'migration':db.scalar(text('SELECT version_num FROM alembic_version'))},
        'assistant':{
            'configured':bool(provider.get('configured')),'route':provider.get('route'),'engine_version':provider.get('engine_version'),
            'profiles_qualified':list(provider.get('profiles_qualified',[])),
            'counts':{**dict(zip(('queued','running','succeeded','failed','awaiting_review'),counts)),'active_watches':watches},
            'live_status':'not_checked',
        },'observed_at':observed.isoformat(),
    }
class CreateUser(DTO):
    username:str=Field(min_length=3,max_length=100)
    display_name:str=Field(min_length=1,max_length=200)
    password:str=Field(min_length=12,max_length=200)
    role:str
    facility_id:str
class UserAction(DTO):
    version:int=Field(strict=True,ge=1)
    target:Literal['active','suspended','disabled']
class Grant(DTO):
    version:int=Field(strict=True,ge=1)
    role:str
    facility_id:str
    active:bool=True
class Reset(DTO):
    version:int=Field(strict=True,ge=1)
    password:str=Field(min_length=12,max_length=200)
def user_dto(u):
    r=serialize(u);r.pop('password_hash');return r

def membership_summaries(db,organization_id,identities):
    grouped={identity:[] for identity in identities}
    if grouped:
        for membership in db.execute(select(Membership.id,Membership.user_id,Membership.role,Membership.facility_id,Membership.active).join(Facility,Facility.id==Membership.facility_id).where(
            Membership.user_id.in_(grouped),Facility.organization_id==organization_id,
        ).order_by(Membership.user_id,Membership.facility_id,Membership.role,Membership.id)).mappings():
            grouped[membership['user_id']].append({key:membership[key] for key in ('id','role','facility_id','active')})
    return grouped

def user_projection():
    return select(User.id,User.organization_id,User.username,User.display_name,User.status,User.version,User.created_at)

def target_user(db,actor,id):
    u=db.scalar(select(User).where(User.id==id,User.organization_id==actor.organization_id).with_for_update())
    if not u:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    return u

def begin(db,actor,key,op,body):
    revalidate_actor(db,actor);require(actor,'identity.admin');return begin_operation(db,actor,key,op,body)
@router.get('/users')
def users(q:str|None=Query(default=None,max_length=120),status:Literal['active','suspended','disabled']|None=None,
          limit:int=Query(default=100,ge=1,le=200),offset:int=Query(default=0,ge=0),actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D34');require(actor,'identity.admin')
    filters=[User.organization_id==actor.organization_id]
    if q and q.strip():
        literal=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        pattern='%'+literal+'%'
        filters.append(User.username.ilike(pattern,escape='\\')|User.display_name.ilike(pattern,escape='\\'))
    if status:filters.append(User.status==status)
    total=db.scalar(select(func.count()).select_from(User).where(*filters))
    rows=db.execute(user_projection().where(*filters).order_by(User.username,User.id).limit(limit).offset(offset)).mappings().all()
    # One joined query, independent of user count; exclude inconsistent cross-org
    # facility memberships rather than disclosing another organization's scope.
    grouped=membership_summaries(db,actor.organization_id,[row['id'] for row in rows])
    return {'items':[{**u,'memberships':grouped[u['id']]} for u in rows],'total':total,'limit':limit,'offset':offset}
@router.get('/users/{id}')
def user_detail(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D34');require(actor,'identity.admin')
    row=db.execute(user_projection().where(User.id==id,User.organization_id==actor.organization_id)).mappings().one_or_none()
    if row is None:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    return {**row,'memberships':membership_summaries(db,actor.organization_id,[id])[id]}
@router.get('/roles')
def roles(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D34')
    return {'items':[{'role':r.id,'permissions':sorted(db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id==r.id)).all()),'declared_template_permissions':sorted(permissions_for({r.id}))} for r in db.scalars(select(Role).order_by(Role.id))],'permissions_source':'persisted_role_permissions'}
@router.get('/users/{id}/memberships')
def memberships(id:str,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require(actor,'identity.admin');target_user(db,actor,id);return {'items':[serialize(m) for m in db.scalars(select(Membership).where(Membership.user_id==id))]}
@router.get('/sessions')
def sessions(actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require(actor,'identity.admin')
    directory={row['id']:dict(row) for row in db.execute(select(User.id,User.username,User.display_name).where(User.organization_id==actor.organization_id)).mappings()}
    return {'items':[{**{k:v for k,v in serialize(s).items() if k not in ('token_hash','csrf_hash','csrf_token')},'user':directory[s.user_id]} for s in db.scalars(select(SessionRecord).where(SessionRecord.user_id.in_(directory)).order_by(SessionRecord.created_at.desc(),SessionRecord.id))]}
@router.post('/users',status_code=201)
def create_user(body:CreateUser,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    payload=body.model_dump();payload['password']=text_hash(body.password);op='admin.create_user';old=begin(db,actor,key,op,payload)
    if old:return old
    if body.role not in ROLE_DOMAINS and body.role not in ALIASES:raise HTTPException(422,detail={'code':'UNKNOWN_ROLE'})
    f=db.get(Facility,body.facility_id)
    if not f or f.organization_id!=actor.organization_id:raise HTTPException(404,detail={'code':'FACILITY_NOT_FOUND'})
    u=User(id=uid(),organization_id=actor.organization_id,username=body.username,display_name=body.display_name,password_hash=password_hasher.hash(body.password));db.add(u);db.flush();db.add(Membership(user_id=u.id,facility_id=f.id,role=body.role));audit(db,actor,'D34',u.id,'created',{'role':body.role});return finish_operation(db,actor,key,op,payload,user_dto(u))
@router.post('/users/{id}/transition')
def user_transition(id:str,body:UserAction,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='admin.user_transition:'+id;payload=body.model_dump();old=begin(db,actor,key,op,payload)
    if old:return old
    u=target_user(db,actor,id)
    if id==actor.user_id:raise HTTPException(409,detail={'code':'SELF_DISABLE_NOT_ALLOWED'})
    transition(u,body.target,{'created':['active'],'active':['suspended','disabled'],'suspended':['active','disabled']},body.version)
    if body.target!='active':
        for s in db.scalars(select(SessionRecord).where(SessionRecord.user_id==id,SessionRecord.revoked_at.is_(None))):s.revoked_at=utcnow()
    audit(db,actor,'D34',id,body.target);return finish_operation(db,actor,key,op,payload,user_dto(u))
@router.post('/users/{id}/memberships')
def grant(id:str,body:Grant,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='admin.membership:'+id;payload=body.model_dump();old=begin(db,actor,key,op,payload)
    if old:return old
    u=target_user(db,actor,id);check_version(u,body.version)
    if body.role not in ROLE_DOMAINS and body.role not in ALIASES:raise HTTPException(422,detail={'code':'UNKNOWN_ROLE'})
    f=db.get(Facility,body.facility_id)
    if not f or f.organization_id!=actor.organization_id:raise HTTPException(404,detail={'code':'FACILITY_NOT_FOUND'})
    m=db.scalar(select(Membership).where(Membership.user_id==id,Membership.facility_id==f.id,Membership.role==body.role))
    if id==actor.user_id and f.id==actor.facility_id and m and m.active and not body.active:
        capable=select(RolePermission.role_id).where(RolePermission.permission_id=='identity.admin')
        if m.role in set(db.scalars(capable)) and not db.scalar(select(Membership.id).where(
            Membership.user_id==id,Membership.facility_id==f.id,Membership.active.is_(True),
            Membership.id!=m.id,Membership.role.in_(capable),
        ).limit(1)):
            raise HTTPException(409,detail={'code':'SELF_LAST_ADMIN_MEMBERSHIP_REQUIRED'})
    if m:m.active=body.active
    else:m=Membership(user_id=id,facility_id=f.id,role=body.role,active=body.active);db.add(m)
    u.version+=1;db.flush();audit(db,actor,'D34',id,'membership_changed',{'role':body.role,'active':body.active,'facility_id':f.id});return finish_operation(db,actor,key,op,payload,{'user':user_dto(u),'membership':serialize(m)})
@router.post('/sessions/{id}/revoke')
def revoke(id:str,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='admin.revoke:'+id;old=begin(db,actor,key,op,{})
    if old:return old
    s=db.get(SessionRecord,id)
    if not s:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    target_user(db,actor,s.user_id);s.revoked_at=utcnow();audit(db,actor,'D34',s.user_id,'session_revoked',{'session_id':id});return finish_operation(db,actor,key,op,{}, {'revoked':True,'id':id})
@router.post('/users/{id}/reset-password')
def reset_password(id:str,body:Reset,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='admin.reset:'+id;payload={'version':body.version,'password_hash':text_hash(body.password)};old=begin(db,actor,key,op,payload)
    if old:return old
    u=target_user(db,actor,id);check_version(u,body.version);u.password_hash=password_hasher.hash(body.password);u.version+=1
    for s in db.scalars(select(SessionRecord).where(SessionRecord.user_id==id,SessionRecord.revoked_at.is_(None))):s.revoked_at=utcnow()
    audit(db,actor,'D34',id,'password_reset');return finish_operation(db,actor,key,op,payload,{'reset':True,'user':user_dto(u)})
class AssignCare(DTO):
    patient_id:str
    active:bool=True
@router.post('/users/{id}/care-assignments')
def care_assign(id:str,body:AssignCare,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    op='admin.care:'+id;payload=body.model_dump();old=begin(db,actor,key,op,payload)
    if old:return old
    target_user(db,actor,id)
    p=db.get(Patient,body.patient_id)
    if not p or p.organization_id!=actor.organization_id or p.facility_id!=actor.facility_id:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    assignment=db.get(CareAssignment,(id,p.id))
    if assignment:assignment.active=body.active
    else:db.add(CareAssignment(user_id=id,patient_id=p.id,active=body.active))
    audit(db,actor,'D34',id,'care_assignment_changed',{'patient_id':p.id,'active':body.active});return finish_operation(db,actor,key,op,payload,payload)
@router.get('/security-events')
def security_events(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    if not ({'system_admin','auditor'} & actor.roles):raise HTTPException(403,detail={'code':'PERMISSION_DENIED'})
    return {'items':[serialize(e) for e in db.scalars(select(SecurityEvent).where(SecurityEvent.organization_id==actor.organization_id,SecurityEvent.facility_id==actor.facility_id).order_by(SecurityEvent.created_at.desc()).limit(200))]}
