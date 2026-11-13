"""Explicit demo proposal pipeline; no endpoint/model SDK in business services."""
import json,time
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import Field
from sqlalchemy import select
from .db import get_db
from .auth import current_actor,revalidate_actor,require_domain,require,scoped_encounter,DTO,actor_for
from .models import *
from .common import *
from .core import record,scope_query
router=APIRouter(tags=['ai-workbench'])
class Propose(DTO):
    task_id:str
    document_id:str
    scenario:Literal['success','failure','timeout','invalid','abstain']='success'
class Review(DTO):
    version:int=Field(strict=True,ge=1)
    action_hash:str=Field(min_length=64,max_length=64)
    decision:Literal['edit','approve','reject']
    edited_text:str|None=Field(default=None,min_length=1,max_length=10000)
class Commit(DTO):
    version:int=Field(strict=True,ge=1)
    action_hash:str=Field(min_length=64,max_length=64)

def proposal_dto(db,p):
    value=serialize(p);v=db.get(DocumentVersion,p.document_version_id);t=db.get(Task,p.task_id)
    value.pop('action_canonical',None);value['action']=json.loads(p.action_canonical)
    value['evidence']={'document_version_id':v.id,'document_id':v.document_id,'content_hash':v.content_hash,'content':v.content,'encounter_version':p.encounter_version,'task_version':p.task_version}
    value['patient_id']=t.patient_id;value['encounter_id']=t.encounter_id;value['demo']=True
    return value

def scoped_proposal(db,actor,id,lock=False):
    p=db.scalar(select(Proposal).where(Proposal.id==id).with_for_update() if lock else select(Proposal).where(Proposal.id==id))
    if not p:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    t=record(db,actor,Task,p.task_id,lock);require_domain(actor,t.domain)
    return p,t

def evidence_current(db,actor,p,t):
    e=scoped_encounter(db,actor,t.encounter_id,True);v=db.get(DocumentVersion,p.document_version_id);d=record(db,actor,Document,v.document_id,True)
    if e.status in ('closed','completed','discharged','cancelled') or e.version!=p.encounter_version or t.version!=p.task_version or d.current_version_id!=v.id or t.status not in ('open','in_progress') or p.expires_at<=utcnow():raise HTTPException(409,detail={'code':'STALE_EVIDENCE_OR_TARGET','outcome':'not_written'})
    if text_hash(v.content)!=v.content_hash or text_hash(p.action_canonical)!=p.action_hash:raise HTTPException(409,detail={'code':'INTEGRITY_MISMATCH','outcome':'not_written'})
    return e,v,d
@router.get('/proposals')
def proposals(task_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D37');require(actor,'documents.content');tasks=db.scalars(scope_query(Task,actor)).all();ids=[t.id for t in tasks if t.domain+'.read' in actor.permissions]
    if task_id:record(db,actor,Task,task_id);ids=[task_id] if task_id in ids else []
    return {'items':[proposal_dto(db,p) for p in db.scalars(select(Proposal).where(Proposal.task_id.in_(ids)).order_by(Proposal.created_at.desc()).limit(100))]}
@router.post('/proposals')
def propose(body:Propose,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D37',True);require(actor,'documents.content');op='proposals.create';payload=body.model_dump();old=begin_operation(db,actor,key,op,payload)
    if old:return old
    t=record(db,actor,Task,body.task_id,True);require_domain(actor,t.domain,True);d=record(db,actor,Document,body.document_id,True);e=scoped_encounter(db,actor,t.encounter_id,True)
    if d.encounter_id!=t.encounter_id or d.patient_id!=t.patient_id:raise HTTPException(404,detail={'code':'CONTEXT_NOT_FOUND'})
    if t.domain!='D37' or t.kind not in ('document_review','imaging_review','dr_review'):raise HTTPException(422,detail={'code':'TASK_NOT_AI_REVIEW_USE_CASE','outcome':'not_written'})
    if t.status not in ('open','in_progress') or e.status=='closed':raise HTTPException(409,detail={'code':'TARGET_CLOSED'})
    v=db.get(DocumentVersion,d.current_version_id)
    from .providers import resolve_provider
    provider=resolve_provider()
    # Immediate deterministic simulation only; no live adapter can enter this transaction.
    start=time.perf_counter_ns();simulation=provider.generate(body.scenario,d.title);outcome=simulation['outcome']
    run=InferenceRun(id=uid(),task_id=t.id,actor_id=actor.user_id,provider='mock_demo',outcome=outcome,reason=None if outcome=='success' else 'Explicit synthetic scenario: '+body.scenario,elapsed_ms=int((time.perf_counter_ns()-start)/1_000_000),measured_cost=None,usage=None);db.add(run);db.flush()
    if outcome!='success':
        audit(db,actor,'D37',run.id,'inference_'+outcome,{'task_id':t.id,'provider':'mock_demo'});return finish_operation(db,actor,key,op,payload,{'run':serialize(run),'proposal':None,'demo':True})
    action=simulation['action'];raw=canonical(action)
    p=Proposal(id=uid(),task_id=t.id,run_id=run.id,document_version_id=v.id,encounter_version=e.version,task_version=t.version,version=1,action_canonical=raw,action_hash=text_hash(raw),expires_at=utcnow()+timedelta(minutes=15));db.add(p);db.flush();db.add(ProposalVersion(proposal_id=p.id,version=1,action_canonical=raw,action_hash=p.action_hash))
    audit(db,actor,'D37',p.id,'proposed',{'task_id':t.id,'document_version_id':v.id,'provider':'mock_demo'});return finish_operation(db,actor,key,op,payload,{'run':serialize(run),'proposal':proposal_dto(db,p),'demo':True})
@router.post('/proposals/{id}/review')
def review(id:str,body:Review,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D37',True);require(actor,'clinical.approve');op='proposals.review:'+id;payload=body.model_dump();old=begin_operation(db,actor,key,op,payload)
    if old:return old
    p,t=scoped_proposal(db,actor,id,True);evidence_current(db,actor,p,t);check_version(p,body.version)
    if p.action_hash!=body.action_hash or p.status not in ('pending','approved'):raise HTTPException(409,detail={'code':'REVIEW_BINDING_STALE','outcome':'not_written'})
    if body.decision!='edit' and body.edited_text is not None:raise HTTPException(422,detail={'code':'EDITS_ONLY_ON_EDIT'})
    db.add(HumanReview(proposal_id=id,actor_id=actor.user_id,version=p.version,action_hash=p.action_hash,decision=body.decision,edited_text=body.edited_text))
    if body.decision=='edit':
        if not body.edited_text:raise HTTPException(422,detail={'code':'EDIT_REQUIRED'})
        p.version+=1;p.action_canonical=canonical({'text':body.edited_text});p.action_hash=text_hash(p.action_canonical);p.status='pending';db.add(ProposalVersion(proposal_id=id,version=p.version,action_canonical=p.action_canonical,action_hash=p.action_hash))
    else:p.status='approved' if body.decision=='approve' else 'rejected'
    audit(db,actor,'D37',id,'review_'+body.decision,{'version':p.version,'action_hash':p.action_hash});return finish_operation(db,actor,key,op,payload,proposal_dto(db,p))

def result_dto(r):
    value=serialize(r);value['proposal_version']=r.version;value['action']=json.loads(r.action_canonical);value.pop('action_canonical',None);return value
@router.post('/proposals/{id}/commit')
def commit(id:str,body:Commit,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D37',True);require(actor,'clinical.approve');op='proposals.commit:'+id;payload=body.model_dump();old=begin_operation(db,actor,key,op,payload)
    if old:
        scoped_proposal(db,actor,id);return old
    p,t=scoped_proposal(db,actor,id,True);check_version(p,body.version)
    if p.status!='approved' or p.action_hash!=body.action_hash:raise HTTPException(409,detail={'code':'APPROVAL_REQUIRED','outcome':'not_written'})
    evidence_current(db,actor,p,t)
    approval=db.scalar(select(HumanReview).where(HumanReview.proposal_id==id,HumanReview.version==p.version,HumanReview.action_hash==p.action_hash,HumanReview.decision=='approve').order_by(HumanReview.created_at.desc()))
    if not approval:raise HTTPException(409,detail={'code':'APPROVAL_REQUIRED','outcome':'not_written'})
    reviewer=db.scalar(select(User).where(User.id==approval.actor_id).with_for_update().execution_options(populate_existing=True))
    memberships=db.scalars(select(Membership).where(Membership.user_id==reviewer.id,Membership.facility_id==actor.facility_id,Membership.active.is_(True))).all()
    from .domains.erp import credential_allows
    granted=db.scalar(select(RolePermission).where(RolePermission.role_id.in_([m.role for m in memberships]),RolePermission.permission_id=='clinical.approve'))
    care=db.get(CareAssignment,(reviewer.id,t.patient_id))
    if reviewer.status!='active' or not granted or not credential_allows(db,reviewer.id,'clinical.approve') or not care or not care.active:raise HTTPException(409,detail={'code':'REVIEWER_PERMISSION_REVOKED','outcome':'not_written'})
    r=CommittedResult(id=uid(),proposal_id=id,task_id=t.id,actor_id=actor.user_id,version=p.version,action_hash=p.action_hash,action_canonical=p.action_canonical,operation_key=key);db.add(r);p.status='committed';t.status='completed';t.version+=1;db.flush()
    audit(db,actor,'D37',id,'committed',{'result_id':r.id,'task_id':t.id,'version':p.version,'operation_key':key});return finish_operation(db,actor,key,op,payload,result_dto(r))
@router.get('/results')
def results(encounter_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D37');q=scope_query(Task,actor)
    if encounter_id:scoped_encounter(db,actor,encounter_id);q=q.where(Task.encounter_id==encounter_id)
    ids=[t.id for t in db.scalars(q) if t.domain+'.read' in actor.permissions]
    return {'items':[result_dto(r) for r in db.scalars(select(CommittedResult).where(CommittedResult.task_id.in_(ids)))]}
@router.get('/runs')
def runs(task_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D37');ids=[t.id for t in db.scalars(scope_query(Task,actor)) if t.domain+'.read' in actor.permissions]
    if task_id:ids=[task_id] if task_id in ids else []
    return {'items':[serialize(r) for r in db.scalars(select(InferenceRun).where(InferenceRun.task_id.in_(ids)).order_by(InferenceRun.created_at.desc()))]}
@router.get('/ai/config')
def ai_config(actor=Depends(current_actor)):
    require_domain(actor,'D37');return {'active_provider':'mock_demo','demo':True,'live_routes_enabled':False,'cost_measured':None,'unknown_revisions':['Qwen 8B','Typhoon','MedGemma'],'declared_capabilities':['demo document review'],'verified_capabilities':[],'verification_evidence':'evidence/fullsystem/core-journeys.json; inspect actual run before claiming verification','external_integration_status':'NOT_CONFIGURED'}
