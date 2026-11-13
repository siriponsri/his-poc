"""Server-verified identities and active memberships. No public demo bearer path."""
from dataclasses import dataclass
from datetime import timedelta
import os,secrets,hmac
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,func,text
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError,VerificationError,InvalidHashError
from .db import get_db
from .models import User,Membership,SessionRecord,LoginAttempt,UserPatientScope,Patient,Encounter,Facility,CareAssignment,RolePermission
from .common import utcnow,text_hash,audit,serialize

password_hasher=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=4)
DUMMY_PASSWORD_HASH=password_hasher.hash(secrets.token_urlsafe(32))
COOKIE='his_session'
ROLE_DOMAINS={
 'registration':['D01','D02','D03','D20','D21','D22'],
 'clinician':['D01','D02','D03','D04','D05','D06','D07','D09','D10','D11','D12','D13','D14','D15','D16','D17','D18','D19','D20','D22','D37'],
 'nurse':['D30','D01','D02','D03','D04','D05','D06','D07','D09','D12','D13','D14','D15','D16','D17','D18','D19','D20','D22'],
 'laboratory':['D01','D03','D07','D10','D22'], 'imaging':['D01','D03','D07','D11','D20','D22','D37'],
 'pharmacist':['D01','D03','D07','D08','D09','D23','D28'], 'billing':['D01','D03','D22','D23','D24','D26','D35'],
 'finance':['D23','D24','D25','D26'], 'inventory':['D27','D28','D29','D31'], 'quality':['D29','D30','D31','D32','D33','D36'],
 'system_admin':['D30','D34','D35','D38'], 'operations_admin':['D38'], 'auditor':[f'D{i:02}' for i in range(1,39)],
 'patient':['D21'],
}
# Domain aliases from the matrix; seeded broad roles remain explicit server grants.
ALIASES={'billing_claims':'billing','inventory_procurement':'inventory','quality_analyst':'quality','identity_admin':'system_admin','backup_operator':'operations_admin','medical_records':'registration','clinical_author':'clinician','reviewer':'clinician','authorized_requester':'clinician','ai_operator':'imaging','patient_portal':'patient','lab':'laboratory','hr_officer':'quality','roster_manager':'quality','credential_reviewer':'quality','staff':'nurse','cssd_operator':'inventory','cssd_release_reviewer':'quality','linen_staff':'inventory','facility_technician':'inventory','quality_officer':'quality','risk_reviewer':'quality','infection_control_officer':'quality','reporting_officer':'quality','report_reviewer':'quality','data_steward':'quality','authorized_analyst':'quality','dataset_reviewer':'quality','integration_operator':'system_admin','integration_admin':'system_admin'}
READ_ONLY={'auditor'}
@dataclass
class Actor:
    user_id:str;username:str;display_name:str;organization_id:str;facility_id:str;roles:set;permissions:set;patient_scope:str|None;session_id:str;care_patient_ids:set|None=None

def permissions_for(roles):
    result=set()
    for raw in roles:
        role=ALIASES.get(raw,raw)
        for domain in ROLE_DOMAINS.get(role,[]):
            result.add(domain+'.read')
            if role not in READ_ONLY: result.update([domain+'.write',domain+'.action'])
        if role in ('clinician','nurse','laboratory','imaging'):result.update(['documents.content','documents.export'])
        if role=='clinician': result.update(['clinical.approve','clinical.attest','orders.sign'])
        if role=='system_admin': result.update(['identity.admin'])
        if role=='quality': result.update(['D33.export','D36.export','D32.restricted'])
        if role in ('billing','finance'):result.add('D24.export')
        if role in ('registration','clinician','nurse','laboratory','imaging','pharmacist','billing','finance','quality','system_admin','auditor','patient'):result.update(['patient.reference','encounter.reference'])
    return result

def actor_for(db,user,session):
    if session.user_id!=user.id:raise HTTPException(401,detail={'code':'SESSION_ACTOR_MISMATCH'})
    facility=db.get(Facility,session.facility_id)
    if not facility or facility.organization_id!=user.organization_id:raise HTTPException(403,detail={'code':'FACILITY_SCOPE_MISMATCH'})
    rows=db.scalars(select(Membership).where(Membership.user_id==user.id,Membership.facility_id==session.facility_id,Membership.active.is_(True))).all()
    if not rows: raise HTTPException(401,detail={'code':'MEMBERSHIP_REVOKED'})
    roles={r.role for r in rows};scope=None
    if any(ALIASES.get(r,r)=='patient' for r in roles):
        scopes=db.scalars(select(UserPatientScope).where(UserPatientScope.user_id==user.id)).all()
        if len(scopes)!=1: raise HTTPException(403,detail={'code':'PORTAL_SCOPE_REQUIRED'})
        scope=scopes[0].patient_id
        # A portal session never accumulates staff privileges.
        roles={'patient'}
    permissions=set(db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id.in_(roles))).all())
    from .domains.erp import credential_allows
    permissions={p for p in permissions if credential_allows(db,user.id,p)}
    care=set(db.scalars(select(CareAssignment.patient_id).where(CareAssignment.user_id==user.id,CareAssignment.active.is_(True))).all()) if {'clinician','nurse'} & roles else None
    return Actor(user.id,user.username,user.display_name,user.organization_id,session.facility_id,roles,permissions,scope,session.id,care)

def current_actor(request:Request,db=Depends(get_db,scope="function")):
    raw=request.cookies.get(COOKIE)
    if not raw: raise HTTPException(401,detail={'code':'SESSION_REQUIRED'})
    session=db.scalar(select(SessionRecord).where(SessionRecord.token_hash==text_hash(raw)))
    if not session or session.revoked_at or session.expires_at<=utcnow(): raise HTTPException(401,detail={'code':'SESSION_EXPIRED_OR_REVOKED'})
    user=db.get(User,session.user_id)
    if not user or user.status!='active': raise HTTPException(401,detail={'code':'ACCOUNT_INACTIVE'})
    if request.method not in ('GET','HEAD','OPTIONS'):
        csrf=request.headers.get('X-CSRF-Token','')
        if not csrf or not hmac.compare_digest(text_hash(csrf),session.csrf_hash): raise HTTPException(403,detail={'code':'CSRF_FAILED'})
    return actor_for(db,user,session)

def revalidate_actor(db,actor):
    # Prototype authorization fence: all scoped mutations serialize against grant/revoke.
    # One organization lock precedes user/entity locks, avoiding reviewer/admin lock inversion.
    lock=int.from_bytes(__import__('hashlib').sha256(('his-authz:'+actor.organization_id).encode()).digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock})
    user=db.scalar(select(User).where(User.id==actor.user_id).with_for_update().execution_options(populate_existing=True))
    session=db.scalar(select(SessionRecord).where(SessionRecord.id==actor.session_id).execution_options(populate_existing=True))
    if not user or user.organization_id!=actor.organization_id or user.status!='active' or not session or session.user_id!=actor.user_id or session.revoked_at or session.expires_at<=utcnow(): raise HTTPException(401,detail={'code':'SESSION_REVOKED'})
    fresh=actor_for(db,user,session)
    actor.roles=fresh.roles;actor.permissions=fresh.permissions;actor.patient_scope=fresh.patient_scope;actor.facility_id=fresh.facility_id;actor.care_patient_ids=fresh.care_patient_ids
    return actor

def require(actor,permission):
    if permission not in actor.permissions: raise HTTPException(403,detail={'code':'PERMISSION_DENIED','permission':permission})

def require_domain(actor,domain,write=False): require(actor,domain+('.write' if write else '.read'))

def scoped_patient(db,actor,id,lock=False):
    q=select(Patient).where(Patient.id==id,Patient.organization_id==actor.organization_id,Patient.facility_id==actor.facility_id)
    if actor.patient_scope:q=q.where(Patient.id==actor.patient_scope)
    if actor.care_patient_ids is not None:q=q.where(Patient.id.in_(actor.care_patient_ids))
    p=db.scalar(q.with_for_update() if lock else q)
    if p is None: raise HTTPException(404,detail={'code':'NOT_FOUND'})
    return p

def scoped_encounter(db,actor,id,lock=False):
    q=select(Encounter).where(Encounter.id==id,Encounter.organization_id==actor.organization_id,Encounter.facility_id==actor.facility_id)
    if actor.patient_scope:q=q.where(Encounter.patient_id==actor.patient_scope)
    if actor.care_patient_ids is not None:q=q.where(Encounter.patient_id.in_(actor.care_patient_ids))
    e=db.scalar(q.with_for_update() if lock else q)
    if e is None:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    return e

def actor_dto(actor):return {'id':actor.user_id,'username':actor.username,'display_name':actor.display_name,'organization_id':actor.organization_id,'facility_id':actor.facility_id,'roles':sorted(actor.roles),'permissions':sorted(actor.permissions),'patient_scope':actor.patient_scope,'care_patient_ids':sorted(actor.care_patient_ids) if actor.care_patient_ids is not None else None}
class DTO(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Login(DTO):
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=1,max_length=200)
class Context(DTO):membership_id:str
router=APIRouter(prefix='/auth',tags=['identity'])
@router.post('/login')
def login(body:Login,request:Request,response:Response,db=Depends(get_db,scope="function")):
    origin=request.headers.get('origin')
    allowed=set(os.getenv('HIS_ALLOWED_ORIGINS','http://localhost:8000,http://127.0.0.1:8000').split(','))
    if origin and origin not in allowed:raise HTTPException(403,detail={'code':'ORIGIN_REJECTED'})
    identity=text_hash(body.username.lower())
    recent=db.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.identity_hash==identity,LoginAttempt.created_at>utcnow()-timedelta(minutes=15),LoginAttempt.successful.is_(False)))
    if recent>=10:raise HTTPException(429,detail={'code':'LOGIN_RATE_LIMITED'})
    user=db.scalar(select(User).where(User.username==body.username))
    valid=False
    try:valid=bool(password_hasher.verify(user.password_hash if user else DUMMY_PASSWORD_HASH,body.password) and user and user.status=='active')
    except (VerifyMismatchError,VerificationError,InvalidHashError):pass
    db.add(LoginAttempt(identity_hash=identity,successful=valid))
    if not valid:
        db.commit() # retain unsuccessful attempts, without logging username/password
        raise HTTPException(401,detail={'code':'INVALID_CREDENTIALS'})
    memberships=db.scalars(select(Membership).where(Membership.user_id==user.id,Membership.active.is_(True)).order_by(Membership.id)).all()
    if not memberships:raise HTTPException(403,detail={'code':'NO_ACTIVE_MEMBERSHIP'})
    raw=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
    session=SessionRecord(user_id=user.id,facility_id=memberships[0].facility_id,token_hash=text_hash(raw),csrf_hash=text_hash(csrf),csrf_token=csrf,expires_at=utcnow()+timedelta(hours=8))
    db.add(session);db.flush();actor=actor_for(db,user,session)
    audit(db,actor,'D34',user.id,'login')
    response.set_cookie(COOKIE,raw,httponly=True,secure=os.getenv('HIS_COOKIE_SECURE','false').lower()=='true',samesite='strict',max_age=28800,path='/')
    return {'user':actor_dto(actor),'csrf_token':csrf,'expires_at':session.expires_at.isoformat()}
@router.get('/me')
def me(actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    session=db.scalar(select(SessionRecord).where(SessionRecord.id==actor.session_id).execution_options(populate_existing=True))
    memberships=db.scalars(select(Membership).where(Membership.user_id==actor.user_id,Membership.active.is_(True))).all()
    return {'user':actor_dto(actor),'csrf_token':session.csrf_token,'expires_at':session.expires_at.isoformat(),'memberships':[serialize(m) for m in memberships]}
@router.post('/logout')
def logout(response:Response,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    revalidate_actor(db,actor);db.get(SessionRecord,actor.session_id).revoked_at=utcnow();audit(db,actor,'D34',actor.user_id,'logout');response.delete_cookie(COOKIE,path='/');return {'ok':True}
@router.post('/context')
def context(body:Context,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    revalidate_actor(db,actor);m=db.get(Membership,body.membership_id)
    if not m or m.user_id!=actor.user_id or not m.active:raise HTTPException(403,detail={'code':'MEMBERSHIP_DENIED'})
    session=db.scalar(select(SessionRecord).where(SessionRecord.id==actor.session_id).execution_options(populate_existing=True));session.facility_id=m.facility_id
    audit(db,actor,'D34',actor.user_id,'scope_change',{'membership_id':m.id})
    return {'user':actor_dto(actor_for(db,db.get(User,actor.user_id),session)),'csrf_token':session.csrf_token,'expires_at':session.expires_at.isoformat()}
