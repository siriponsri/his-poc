"""Staff assistant API. Reads never dispatch or enqueue a generation."""
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import Field
from sqlalchemy import select, func
from .auth import DTO, current_actor, revalidate_actor
from .db import get_db
from .models import Task
from .models_assistant import AssistantRun, AssistantWatch
from .assistant_profiles import PROFILES, LIMITS, available, require_profile, allowed_effects
from .assistant_collectors import eligible_contexts, collect_packet
from .assistant_core import enqueue, scoped_run, run_dto, watch_dto, create_watch, actor_fence
from .assistant_effects import apply_run
from .core import scope_query
from .common import begin_operation, finish_operation, authorization_hash, audit, utcnow

router=APIRouter(prefix='/assistant',tags=['assistant'])
Profile=Literal['visit_preparation','nursing_handover','records_readiness','laboratory_handoff']

class RunInput(DTO):
    profile:Profile
    patient_id:str=Field(min_length=1,max_length=64)
    encounter_id:str=Field(min_length=1,max_length=64)
    locale:Literal['th','en']='th'
    expected_source_digest:str|None=Field(default=None,pattern='^[a-f0-9]{64}$')

class BatchInput(DTO):
    profile:Profile
    selection:Literal['my_eligible_work']='my_eligible_work'
    maximum_contexts:int=Field(default=6,ge=1,le=6,strict=True)
    keep_prepared:bool=False
    watch_minutes:int=Field(default=30,ge=1,le=30,strict=True)
    locale:Literal['th','en']='th'

class WatchInput(DTO):
    profile:Profile
    patient_id:str=Field(min_length=1,max_length=64)
    encounter_id:str=Field(min_length=1,max_length=64)
    locale:Literal['th','en']='th'
    watch_minutes:int=Field(default=30,ge=1,le=30,strict=True)

class ApplyInput(DTO):
    expected_revision_id:str=Field(min_length=1,max_length=64)
    expected_version:int=Field(ge=1,strict=True)
    expected_content_hash:str=Field(pattern='^[a-f0-9]{64}$')
    expected_source_digest:str=Field(pattern='^[a-f0-9]{64}$')
    selected_action_ids:list[str]=Field(default_factory=list,max_length=8)
    edited_draft_text:str|None=Field(default=None,min_length=1,max_length=100000)
    decision:Literal['accepted','rejected']='accepted'

def _provider_config():
    from .assistant_provider import assistant_provider_config
    return assistant_provider_config()

@router.get('/config')
def config(actor=Depends(current_actor)):
    provider=_provider_config()
    profiles=[{'id':key,'label':p['label'],'available':available(actor,key),'allowed_effects':allowed_effects(actor,key)} for key,p in PROFILES.items()]
    preferred=next((p for role,p in (('laboratory','laboratory_handoff'),('nurse','nursing_handover'),('clinician','visit_preparation'),('registration','records_readiness')) if role in actor.roles and available(actor,p)),None)
    return {'enabled':bool(provider.get('enabled')) and any(p['available'] for p in profiles),'profiles':profiles,'default_profile':preferred or next((p['id'] for p in profiles if p['available']),None),'provider':provider,'limits':LIMITS}

def _visible_watches(db,actor):
    rows=[]
    for w in db.scalars(select(AssistantWatch).where(AssistantWatch.actor_id==actor.user_id,AssistantWatch.organization_id==actor.organization_id,AssistantWatch.facility_id==actor.facility_id).order_by(AssistantWatch.created_at.desc()).limit(100)):
        if available(actor,w.profile) and w.authorization_hash==authorization_hash(actor):
            try:collect_packet(db,actor,w.profile,w.patient_id,w.encounter_id,w.locale)
            except HTTPException:continue
            item=watch_dto(w)
            if w.status=='active' and w.expires_at<=utcnow():item['status']='expired'
            rows.append(item)
    return rows

@router.get('/worklist')
def worklist(profile:Profile|None=None,patient_id:str|None=None,encounter_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    if profile:require_profile(actor,profile)
    allowed=[p for p in PROFILES if available(actor,p)]
    if not allowed:raise HTTPException(403,detail={'code':'ASSISTANT_PROFILE_FORBIDDEN'})
    q=select(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.organization_id==actor.organization_id,AssistantRun.facility_id==actor.facility_id,AssistantRun.profile.in_([profile] if profile else allowed)).order_by(AssistantRun.created_at.desc()).limit(100)
    if patient_id:q=q.where(AssistantRun.patient_id==patient_id)
    if encounter_id:q=q.where(AssistantRun.encounter_id==encounter_id)
    items=[]
    for run in db.scalars(q):
        try:items.append(run_dto(db,actor,run))
        except HTTPException:continue
    contexts=[]
    for p in ([profile] if profile else allowed):
        contexts.extend(c for c in eligible_contexts(db,actor,p) if (not patient_id or c['patient_id']==patient_id) and (not encounter_id or c['encounter_id']==encounter_id))
    counts={state:sum(item['execution_state']==state for item in items) for state in ('queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted')}
    counts['awaiting_review']=sum(item['review_state']=='pending' for item in items)
    return {'items':items,'eligible_contexts':contexts,'watches':_visible_watches(db,actor),'counts':counts,'scope':'authorized_work'}

@router.post('/runs',status_code=202)
def create_run(body:RunInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    actor_fence(db,actor);require_profile(actor,body.profile)
    payload=body.model_dump();op='assistant.runs.create';old=begin_operation(db,actor,key,op,payload)
    if old:
        run,packet=scoped_run(db,actor,old['run']['id']);return {'run':run_dto(db,actor,run,packet),'reused':True}
    run,reused=enqueue(db,actor,body.profile,body.patient_id,body.encounter_id,body.locale,key,body.expected_source_digest)
    return finish_operation(db,actor,key,op,payload,{'run':run_dto(db,actor,run),'reused':reused})

@router.get('/runs/{id}')
def get_run(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    run,packet=scoped_run(db,actor,id);return run_dto(db,actor,run,packet)

@router.post('/batches',status_code=202)
def batch(body:BatchInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    actor_fence(db,actor);require_profile(actor,body.profile)
    payload=body.model_dump();op='assistant.batch';old=begin_operation(db,actor,key,op,payload)
    if old:
        for row in old['runs']:scoped_run(db,actor,row['id'])
        return old
    contexts=eligible_contexts(db,actor,body.profile);runs=[];watches=[]
    from .common import digest
    for context in contexts[:body.maximum_contexts]:
        run,_=enqueue(db,actor,body.profile,context['patient_id'],context['encounter_id'],body.locale,'batch:'+digest({'actor':actor.user_id,'key':key,'encounter':context['encounter_id']})[:64])
        runs.append(run_dto(db,actor,run))
        if body.keep_prepared:watches.append(watch_dto(create_watch(db,actor,body.profile,run.patient_id,run.encounter_id,body.locale,body.watch_minutes,run)))
    return finish_operation(db,actor,key,op,payload,{'runs':runs,'watches':watches,'eligible_context_count':len(contexts),'scope':'authorized_work'})

@router.post('/watches',status_code=201)
def enable_watch(body:WatchInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    actor_fence(db,actor);require_profile(actor,body.profile)
    payload=body.model_dump();op='assistant.watch';old=begin_operation(db,actor,key,op,payload)
    if old:
        collect_packet(db,actor,body.profile,body.patient_id,body.encounter_id,body.locale);return old
    watch=create_watch(db,actor,body.profile,body.patient_id,body.encounter_id,body.locale,body.watch_minutes)
    return finish_operation(db,actor,key,op,payload,{'watch':watch_dto(watch)})

@router.get('/watches')
def watches(actor=Depends(current_actor),db=Depends(get_db,scope='function')):return {'watches':_visible_watches(db,actor)}

@router.post('/watches/{id}/pause')
def pause_watch(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    actor_fence(db,actor)
    watch=db.scalar(select(AssistantWatch).where(AssistantWatch.id==id,AssistantWatch.actor_id==actor.user_id,AssistantWatch.facility_id==actor.facility_id).with_for_update())
    if not watch:raise HTTPException(404,detail={'code':'ASSISTANT_WATCH_NOT_FOUND'})
    require_profile(actor,watch.profile);collect_packet(db,actor,watch.profile,watch.patient_id,watch.encounter_id,watch.locale)
    op='assistant.watch.pause:'+id;old=begin_operation(db,actor,key,op,{})
    if old:return old
    watch.status='paused';audit(db,actor,PROFILES[watch.profile]['domains'][0],id,'assistant_watch_paused',{})
    return finish_operation(db,actor,key,op,{}, {'watch':watch_dto(watch)})

@router.post('/runs/{id}/apply')
def apply(id:str,body:ApplyInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    actor_fence(db,actor);scoped_run(db,actor,id)
    op='assistant.apply:'+id;payload=body.model_dump();old=begin_operation(db,actor,key,op,payload)
    if old:return old
    return finish_operation(db,actor,key,op,payload,apply_run(db,actor,id,body))

ZONES=(('registration','Registration',('D01','D22'),'records_readiness'),('outpatient','Outpatient',('D03',),'visit_preparation'),('nursing','Nursing',('D06',),'nursing_handover'),('laboratory','Laboratory',('D10',),'laboratory_handoff'),('records','Medical records',('D22',),'records_readiness'),('ai_workspace','AI workspace',('D37',),'visit_preparation'))

@router.get('/operations-map')
def operations_map(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    zones=[];agents=[]
    for key,label,domains,profile in ZONES:
        permitted=available(actor,profile)
        zone={'id':key,'label':label,'domains':list(domains),'available':permitted,'open_task_count':None,'awaiting_review_count':None}
        if permitted:
            zone['open_task_count']=len(db.scalars(scope_query(Task,actor).where(Task.domain.in_([d for d in domains if d+'.read' in actor.permissions]),Task.status.in_(['open','in_progress']))).all())
            rows=[]
            for run in db.scalars(select(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.profile==profile,AssistantRun.facility_id==actor.facility_id).order_by(AssistantRun.created_at.desc()).limit(100)):
                try:rows.append(run_dto(db,actor,run))
                except HTTPException:continue
            zone['awaiting_review_count']=sum(r['review_state']=='pending' for r in rows)
        zones.append(zone)
    for profile,definition in PROFILES.items():
        if not available(actor,profile):continue
        rows=[]
        for run in db.scalars(select(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.facility_id==actor.facility_id,AssistantRun.profile==profile).order_by(AssistantRun.created_at.desc()).limit(20)):
            try:rows.append(run_dto(db,actor,run))
            except HTTPException:continue
        if rows:
            current=next((r for r in rows if r['execution_state'] in ('running','queued','waiting_for_capacity')),rows[0])
            agents.append({'profile':profile,'label':definition['label'],'run_id':current['id'],'execution_state':current['execution_state'],'review_state':current['review_state'],'patient_label':current['patient_label']})
    return {'scope':'authorized_work','refreshed_at':utcnow().isoformat(),'zones':zones,'agents':agents}
