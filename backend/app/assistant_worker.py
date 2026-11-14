"""Durable assistant worker. Run `python -m backend.app.assistant_worker` separately.

No request/render hook calls this worker. Provider I/O happens with its DB session closed.
"""
import argparse
import hashlib
import time
from datetime import timedelta
from types import SimpleNamespace
from fastapi import HTTPException
from sqlalchemy import select, text
from .db import SessionLocal
from . import models as M
from .models_assistant import AssistantRun, AssistantRevision, AssistantWatch
from .assistant_core import actor_fence, enqueue, QUEUED
from .assistant_collectors import collect_packet
from .assistant_profiles import PROFILES
from .assistant_admission import admission_busy
from .auth import actor_for
from .common import utcnow, authorization_hash, digest, uid, audit

def stored_actor(db,actor_id,session_id):
    user=db.get(M.User,actor_id);session=db.get(M.SessionRecord,session_id)
    if not user or user.status!='active' or not session or session.user_id!=actor_id or session.revoked_at or session.expires_at<=utcnow():
        raise HTTPException(401,detail={'code':'ASSISTANT_SESSION_REVOKED'})
    actor=actor_for(db,user,session)
    actor_fence(db,actor)
    return actor

def _receipt_actor(row):
    # Only identifies an existing immutable actor/scope for a revocation audit;
    # never authorizes a read, generation or effect.
    return SimpleNamespace(user_id=row.actor_id,organization_id=row.organization_id,facility_id=row.facility_id)

def scan_watches_once(session_factory=SessionLocal,now=None):
    now=now or utcnow();counts={'scanned':0,'enqueued':0,'revoked':0}
    with session_factory() as db:
        ids=list(db.scalars(select(AssistantWatch.id).where(AssistantWatch.status=='active',AssistantWatch.next_scan_at<=now).order_by(AssistantWatch.next_scan_at,AssistantWatch.id).limit(100)))
    for watch_id in ids:
        try:
            with session_factory.begin() as db:
                initial=db.get(AssistantWatch,watch_id)
                actor=stored_actor(db,initial.actor_id,initial.session_id)
                watch=db.scalar(select(AssistantWatch).where(AssistantWatch.id==watch_id).with_for_update(skip_locked=True).execution_options(populate_existing=True))
                if not watch or watch.status!='active' or watch.next_scan_at>now:continue
                counts['scanned']+=1
                if watch.expires_at<=now:
                    watch.status='expired';continue
                if watch.auto_run_count>=watch.max_auto_runs:
                    watch.status='exhausted';continue
                if watch.authorization_hash!=authorization_hash(actor):raise HTTPException(403,detail={'code':'ASSISTANT_AUTHORIZATION_CHANGED'})
                packet=collect_packet(db,actor,watch.profile,watch.patient_id,watch.encounter_id,watch.locale)
                watch.next_scan_at=now+timedelta(seconds=30)
                if watch.last_source_digest==packet['source_digest']:continue
                if watch.last_enqueued_at and (now-watch.last_enqueued_at).total_seconds()<60:continue
                key='watch:'+digest({'watch':watch.id,'source':packet['source_digest']})[:64]
                run,reused=enqueue(db,actor,watch.profile,watch.patient_id,watch.encounter_id,watch.locale,key)
                watch.last_source_digest=packet['source_digest'];watch.last_run_id=run.id
                if not reused:
                    watch.last_enqueued_at=now;watch.auto_run_count+=1;counts['enqueued']+=1
                if watch.auto_run_count>=watch.max_auto_runs:watch.status='exhausted'
        except HTTPException as exc:
            if exc.status_code==429:
                with session_factory.begin() as db:
                    watch=db.get(AssistantWatch,watch_id,with_for_update=True)
                    watch.next_scan_at=now+timedelta(seconds=30)
                continue
            with session_factory.begin() as db:
                watch=db.get(AssistantWatch,watch_id,with_for_update=True)
                if watch and watch.status=='active':
                    watch.status='revoked';counts['revoked']+=1
                    audit(db,_receipt_actor(watch),PROFILES[watch.profile]['domains'][0],watch.id,'assistant_watch_revoked',{'reason':'AUTHORIZATION_OR_SCOPE_CHANGED'})
    return counts

def _recover_expired(db,now):
    organizations=sorted(set(db.scalars(select(AssistantRun.organization_id).where(AssistantRun.execution_state=='running',AssistantRun.lease_expires_at<=now))))
    # Match the normal authorization->entity lock order before FK-backed auditing.
    for organization in organizations:
        key=int.from_bytes(hashlib.sha256(('his-authz:'+organization).encode()).digest()[:8],'big',signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':key})
    for run in db.scalars(select(AssistantRun).where(AssistantRun.execution_state=='running',AssistantRun.lease_expires_at<=now).with_for_update(skip_locked=True)):
        run.execution_state='interrupted';run.review_state='unavailable';run.error='WORKER_LEASE_EXPIRED';run.completed_at=now
        audit(db,_receipt_actor(run),PROFILES[run.profile]['domains'][0],run.id,'assistant_interrupted',{'reason':'WORKER_LEASE_EXPIRED','automatic_retry':False})

def run_once(session_factory=SessionLocal,prepare=None,validate=None,config=None,now=None,clock=utcnow):
    """Dispatch at most one queued run. Dependency injection is for offline test doubles."""
    fixed_now=now
    now=fixed_now if fixed_now is not None else clock()
    if prepare is None or validate is None or config is None:
        from .assistant_provider import prepare_assistant, validate_assistant_artifact, assistant_provider_config
        prepare=prepare or prepare_assistant;validate=validate or validate_assistant_artifact;config=config or assistant_provider_config
    with session_factory.begin() as db:_recover_expired(db,now)
    with session_factory() as db:
        ids=list(db.scalars(select(AssistantRun.id).where(AssistantRun.execution_state.in_(QUEUED)).order_by(AssistantRun.created_at,AssistantRun.id).limit(6)))
    for run_id in ids:
        try:
            with session_factory.begin() as db:
                initial=db.get(AssistantRun,run_id)
                actor=stored_actor(db,initial.actor_id,initial.session_id)
                run=db.scalar(select(AssistantRun).where(AssistantRun.id==run_id).with_for_update(skip_locked=True).execution_options(populate_existing=True))
                if not run or run.execution_state not in QUEUED:continue
                packet=collect_packet(db,actor,run.profile,run.patient_id,run.encounter_id,run.locale)
                if authorization_hash(actor)!=run.authorization_hash or packet['source_digest']!=run.source_digest:
                    run.execution_state='stale_context';run.error='SOURCE_OR_AUTHORIZATION_CHANGED';run.completed_at=now
                    audit(db,actor,PROFILES[run.profile]['domains'][0],run.id,'assistant_stale_context',{'reason':run.error})
                    continue
                provider=config()
                if (not provider.get('configured') or not provider.get('enabled',True) or not provider.get('qualified') or run.profile not in provider.get('profiles_qualified',[])):
                    run.execution_state='failed';run.error='ASSISTANT_PROVIDER_NOT_QUALIFIED';run.provider=provider;run.completed_at=now
                    audit(db,actor,PROFILES[run.profile]['domains'][0],run.id,'assistant_failed',{'reason':run.error})
                    continue
                if admission_busy(db,assistant_id=run.id,now=fixed_now):
                    run.execution_state='waiting_for_capacity';continue
                # Authorization/source/global admission locks may have waited. Start the
                # reservation from a fresh clock while the global lock is still held.
                reservation_now=fixed_now if fixed_now is not None else clock()
                timeout=min(300,max(1,int(provider.get('timeout_seconds',180))))
                run.execution_state='running';run.lease_id=uid();run.started_at=reservation_now
                run.lease_expires_at=reservation_now+timedelta(seconds=timeout+60)
                run.hold_until=reservation_now+timedelta(seconds=timeout+120)
                run.provider=provider
                lease_id=run.lease_id;profile=run.profile;locale=run.locale;view=run.inference_view
                audit(db,actor,PROFILES[profile]['domains'][0],run.id,'assistant_started',{'profile':profile,'input_hash':run.input_hash})
        except HTTPException:
            with session_factory.begin() as db:
                run=db.get(AssistantRun,run_id,with_for_update=True)
                if run and run.execution_state in QUEUED:
                    run.execution_state='stale_context';run.error='AUTHORIZATION_OR_SCOPE_CHANGED';run.completed_at=now
                    audit(db,_receipt_actor(run),PROFILES[run.profile]['domains'][0],run.id,'assistant_revoked',{})
            continue
        with session_factory() as db:
            state=db.get(AssistantRun,run_id).execution_state
        if state!='running':continue
        # All sessions/transactions used for admission are closed before provider I/O.
        started=time.perf_counter_ns()
        try:result=prepare(profile,locale,view)
        except Exception:result={'outcome':'failed','reason':'ASSISTANT_PROVIDER_ERROR','artifact':None,'provenance':{},'usage':None,'measured_cost':None}
        elapsed=int((time.perf_counter_ns()-started)/1_000_000)
        try:
            with session_factory.begin() as db:
                initial=db.get(AssistantRun,run_id)
                actor=stored_actor(db,initial.actor_id,initial.session_id)
                run=db.get(AssistantRun,run_id,with_for_update=True)
                if run.execution_state!='running' or run.lease_id!=lease_id:
                    if run.lease_id==lease_id:
                        run.provider={**(run.provider or {}),'late_provider_outcome':result.get('outcome'),'provenance':result.get('provenance',{}),'elapsed_ms':elapsed}
                        run.usage=result.get('usage')
                    return {'dispatched':1,'run_id':run_id,'state':run.execution_state}
                packet=collect_packet(db,actor,profile,run.patient_id,run.encounter_id,locale)
                outcome=result.get('outcome','invalid_output')
                if outcome not in ('success','failed','timeout','invalid_output','abstained'):outcome='invalid_output'
                run.provider={**(run.provider or {}),'provenance':result.get('provenance',{}),'elapsed_ms':result.get('elapsed_ms',elapsed),'provider_outcome':outcome}
                run.usage=result.get('usage');run.measured_cost=None
                run.error=result.get('reason');run.completed_at=utcnow()
                if authorization_hash(actor)!=run.authorization_hash or packet['source_digest']!=run.source_digest:
                    outcome='stale_context';run.error='SOURCE_OR_AUTHORIZATION_CHANGED'
                elif run.completed_at>run.lease_expires_at:
                    outcome='interrupted';run.error='INFERENCE_LEASE_EXPIRED'
                if outcome=='success':
                    try:artifact=validate(profile,result.get('artifact'),run.inference_view)
                    except (ValueError,TypeError):outcome='invalid_output';run.error='ASSISTANT_ARTIFACT_INVALID'
                    else:
                        db.add(AssistantRevision(id=uid(),run_id=run.id,version=1,content_hash=digest(artifact),source_digest=run.source_digest,artifact=artifact,origin='model',created_by=actor.user_id))
                        run.review_state='pending'
                run.execution_state='succeeded' if outcome=='success' else outcome
                # A stale packet does not prove an already timed-out remote job stopped.
                if outcome not in ('timeout','interrupted') and result.get('outcome')!='timeout':run.hold_until=None
                audit(db,actor,PROFILES[profile]['domains'][0],run.id,'assistant_'+run.execution_state,{'provider_outcome':result.get('outcome'),'automatic_retry':False})
        except HTTPException:
            with session_factory.begin() as db:
                run=db.get(AssistantRun,run_id,with_for_update=True)
                if run and run.execution_state=='running':
                    run.execution_state='stale_context';run.review_state='unavailable';run.error='AUTHORIZATION_OR_SCOPE_CHANGED';run.completed_at=utcnow()
                    run.provider={**(run.provider or {}),'provenance':result.get('provenance',{}),'provider_outcome':result.get('outcome'),'elapsed_ms':elapsed};run.usage=result.get('usage')
                    if result.get('outcome')!='timeout':run.hold_until=None
                    audit(db,_receipt_actor(run),PROFILES[profile]['domains'][0],run.id,'assistant_revoked',{})
        with session_factory() as db:return {'dispatched':1,'run_id':run_id,'state':db.get(AssistantRun,run_id).execution_state}
    return {'dispatched':0}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--poll-seconds',type=int,default=5)
    args=parser.parse_args()
    while True:
        scan_watches_once();run_once()
        if args.once:return
        time.sleep(min(30,max(1,args.poll_seconds)))

if __name__=='__main__':main()
