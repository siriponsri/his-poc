from typing import Literal
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import Field
from sqlalchemy import select
from .db import get_db
from .auth import *
from .models import *
from .common import *
router=APIRouter(prefix='/admin',tags=['administration'])
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

def target_user(db,actor,id):
    u=db.scalar(select(User).where(User.id==id,User.organization_id==actor.organization_id).with_for_update())
    if not u:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    return u

def begin(db,actor,key,op,body):
    revalidate_actor(db,actor);require(actor,'identity.admin');return begin_operation(db,actor,key,op,body)
@router.get('/users')
def users(actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D34');require(actor,'identity.admin');return {'items':[user_dto(u) for u in db.scalars(select(User).where(User.organization_id==actor.organization_id))]}
@router.get('/roles')
def roles(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D34')
    return {'items':[{'role':r.id,'permissions':sorted(db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id==r.id)).all()),'declared_template_permissions':sorted(permissions_for({r.id}))} for r in db.scalars(select(Role).order_by(Role.id))],'permissions_source':'persisted_role_permissions'}
@router.get('/users/{id}/memberships')
def memberships(id:str,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require(actor,'identity.admin');target_user(db,actor,id);return {'items':[serialize(m) for m in db.scalars(select(Membership).where(Membership.user_id==id))]}
@router.get('/sessions')
def sessions(actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require(actor,'identity.admin');ids=db.scalars(select(User.id).where(User.organization_id==actor.organization_id)).all()
    return {'items':[{k:v for k,v in serialize(s).items() if k not in ('token_hash','csrf_hash','csrf_token')} for s in db.scalars(select(SessionRecord).where(SessionRecord.user_id.in_(ids)))]}
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
    u=target_user(db,actor,id)
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
