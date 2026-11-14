"""Scoped assistant queue, read DTOs and watch commands. No generation on reads."""
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, func, text
from . import models as M
from .models_assistant import AssistantRun, AssistantRevision, AssistantEffect, AssistantWatch
from .assistant_profiles import PROFILES, LIMITS, available, require_profile
from .assistant_collectors import collect_packet, eligible_contexts
from .auth import revalidate_actor
from .common import authorization_hash, digest, serialize, audit, utcnow, uid

QUEUED=('queued','waiting_for_capacity')

def actor_fence(db,actor):
    revalidate_actor(db,actor)
    db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'assistant-actor:'+actor.user_id})

def scoped_run(db, actor, run_id, lock=False):
    q=select(AssistantRun).where(AssistantRun.id==run_id,AssistantRun.actor_id==actor.user_id,AssistantRun.organization_id==actor.organization_id,AssistantRun.facility_id==actor.facility_id)
    if lock:q=q.with_for_update()
    run=db.scalar(q.execution_options(populate_existing=True))
    if not run:raise HTTPException(404,detail={'code':'ASSISTANT_RUN_NOT_FOUND'})
    require_profile(actor,run.profile)
    packet=collect_packet(db,actor,run.profile,run.patient_id,run.encounter_id,run.locale)
    # An artifact made with a different capability set must not disclose the old packet.
    if run.authorization_hash!=authorization_hash(actor):
        raise HTTPException(403,detail={'code':'ASSISTANT_AUTHORIZATION_CHANGED'})
    return run,packet

def run_dto(db,actor,run,packet=None):
    if packet is None:
        run,packet=scoped_run(db,actor,run.id)
    revision=db.scalar(select(AssistantRevision).where(AssistantRevision.run_id==run.id).order_by(AssistantRevision.version.desc()))
    fresh=packet['source_digest']==run.source_digest
    result={k:getattr(run,k) for k in ('id','profile','patient_id','encounter_id','execution_state','review_state','source_digest','provider','usage','measured_cost','error')}
    sources=[{key:value for key,value in source.items() if key in ('ref','kind','fields','text','label')} for source in run.source_manifest['sources'] if source.get('ref')]
    result.update(patient_label=run.source_manifest['patient_label'],source_freshness='current' if fresh else 'stale',coverage=run.inference_view['coverage'],sources=sources,revision=None,effects=[effect_dto(e) for e in db.scalars(select(AssistantEffect).where(AssistantEffect.run_id==run.id))],created_at=run.created_at.isoformat(),completed_at=run.completed_at.isoformat() if run.completed_at else None)
    if not fresh:result['review_state']='stale'
    if revision:result['revision']={'id':revision.id,'version':revision.version,'content_hash':revision.content_hash,'origin':revision.origin,**revision.artifact}
    from .assistant_reconciliation import admission_status
    result['admission']=admission_status(db,run,'assistant')
    return result

def effect_dto(effect):
    return {'id':effect.id,'action_id':effect.action_id,'kind':effect.kind,'domain':effect.receipt.get('domain'),'state':'applied','task_id':effect.task_id,'document_id':effect.document_id,'receipt':effect.receipt}

def enqueue(db,actor,profile,patient_id,encounter_id,locale,key,expected_digest=None):
    actor_fence(db,actor)
    packet=collect_packet(db,actor,profile,patient_id,encounter_id,locale)
    encounter=next(s for s in packet['manifest']['sources'] if s['kind']=='encounter')
    if encounter['fields']['status'] in ('closed','completed','discharged','cancelled'):
        raise HTTPException(409,detail={'code':'ASSISTANT_CONTEXT_CLOSED'})
    if expected_digest and packet['source_digest']!=expected_digest:raise HTTPException(409,detail={'code':'ASSISTANT_SOURCE_CHANGED'})
    request_hash=digest({'profile':profile,'patient_id':patient_id,'encounter_id':encounter_id,'locale':locale,'expected_source_digest':expected_digest})
    prior=db.scalar(select(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.operation_key==key))
    if prior:
        if prior.request_hash!=request_hash or prior.authorization_hash!=authorization_hash(actor):raise HTTPException(409,detail={'code':'IDEMPOTENCY_CONFLICT'})
        return prior,True
    same=select(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.profile==profile,AssistantRun.patient_id==patient_id,AssistantRun.encounter_id==encounter_id,AssistantRun.source_digest==packet['source_digest'],AssistantRun.authorization_hash==authorization_hash(actor)).order_by(AssistantRun.created_at.desc())
    prior=db.scalar(same)
    # Failed and timeout attempts are also immutable attempts, never automatic retries.
    if prior:return prior,True
    count=db.scalar(select(func.count()).select_from(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.execution_state.in_(QUEUED)))
    old=db.scalars(select(AssistantRun).where(AssistantRun.actor_id==actor.user_id,AssistantRun.profile==profile,AssistantRun.patient_id==patient_id,AssistantRun.encounter_id==encounter_id,AssistantRun.execution_state.in_(QUEUED)).with_for_update()).all()
    if count-len(old)>=LIMITS['maximum_queued_runs']:raise HTTPException(429,detail={'code':'ASSISTANT_QUEUE_LIMIT'})
    for superseded in old:
        superseded.execution_state='stale_context';superseded.review_state='superseded';superseded.error='NEWER_SOURCE_QUEUED';superseded.completed_at=utcnow()
    run=AssistantRun(id=uid(),organization_id=actor.organization_id,facility_id=actor.facility_id,patient_id=patient_id,encounter_id=encounter_id,actor_id=actor.user_id,session_id=actor.session_id,profile=profile,locale=locale,authorization_hash=authorization_hash(actor),operation_key=key,request_hash=request_hash,source_digest=packet['source_digest'],source_manifest=packet['manifest'],inference_view=packet['view'],input_hash=packet['input_hash'],execution_state='queued',review_state='unavailable',provider={})
    db.add(run);db.flush()
    audit(db,actor,PROFILES[profile]['domains'][0],run.id,'assistant_queued',{'profile':profile,'source_digest':run.source_digest,'coverage':run.inference_view['coverage']})
    return run,False

def watch_dto(w):
    return {k:serialize(w)[k] for k in ('id','profile','patient_id','encounter_id','status','expires_at','last_run_id','next_scan_at','auto_run_count','max_auto_runs')}

def create_watch(db,actor,profile,patient_id,encounter_id,locale='th',minutes=30,last_run=None):
    actor_fence(db,actor)
    packet=collect_packet(db,actor,profile,patient_id,encounter_id,locale)
    now=utcnow()
    existing=db.scalar(select(AssistantWatch).where(AssistantWatch.actor_id==actor.user_id,AssistantWatch.session_id==actor.session_id,AssistantWatch.profile==profile,AssistantWatch.patient_id==patient_id,AssistantWatch.encounter_id==encounter_id,AssistantWatch.status=='active',AssistantWatch.expires_at>now))
    if existing:return existing
    count=db.scalar(select(func.count()).select_from(AssistantWatch).where(AssistantWatch.actor_id==actor.user_id,AssistantWatch.status=='active',AssistantWatch.expires_at>now))
    if count>=LIMITS['maximum_active_watches']:raise HTTPException(429,detail={'code':'ASSISTANT_WATCH_LIMIT'})
    watch=AssistantWatch(id=uid(),actor_id=actor.user_id,session_id=actor.session_id,organization_id=actor.organization_id,facility_id=actor.facility_id,patient_id=patient_id,encounter_id=encounter_id,profile=profile,locale=locale,authorization_hash=authorization_hash(actor),status='active',expires_at=now+timedelta(minutes=min(30,minutes)),next_scan_at=now+timedelta(seconds=30),last_source_digest=packet['source_digest'],last_run_id=last_run.id if last_run else None,last_enqueued_at=now if last_run else None,auto_run_count=0,max_auto_runs=3)
    db.add(watch);db.flush();audit(db,actor,PROFILES[profile]['domains'][0],watch.id,'assistant_watch_enabled',{'expires_at':watch.expires_at.isoformat()})
    return watch
