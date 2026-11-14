"""Trusted audited evidence; no HTTP reconciliation route exists. TTL/ps[] cannot clear UNKNOWN."""
from datetime import timedelta
from fastapi import HTTPException
from .models import AuditEvent, Task, InferenceRun
from .models_assistant import AssistantRun
from .common import digest, uid, utcnow

ACKNOWLEDGEMENT='I confirm HIS workers are quiesced and the pinned provider is drained'
ASSISTANT_UNKNOWN={'ASSISTANT_PROVIDER_CONNECTION_FAILED','ASSISTANT_PROVIDER_ERROR'}
LEGACY_UNKNOWN={'PROVIDER_CONNECTION_FAILED','PROVIDER_UNEXPECTED_ERROR'}

def _container(run,kind):return run.provider if kind=='assistant' else run.provenance

def _scope(db,run,kind):
    if kind=='assistant':return run.organization_id,run.facility_id
    task=db.get(Task,run.task_id)
    return task.organization_id,task.facility_id

def _binding(run,kind):
    if kind=='assistant':identity={'id':run.id,'actor_id':run.actor_id,'lease_id':run.lease_id,'source_digest':run.source_digest,'input_hash':run.input_hash}
    else:identity={'id':run.id,'actor_id':run.actor_id,'task_id':run.task_id,'request_hash':run.request_hash,'created_at':run.created_at,'context_snapshot':run.context_snapshot}
    return digest({'kind':kind,'identity':identity})

def _write_marker(db,run,kind,actor,key,action,details):
    organization_id,facility_id=_scope(db,run,kind)
    marker={'version':1,'run_kind':kind,'run_id':run.id,'attempt_binding':_binding(run,kind),'actor_id':actor.user_id,'recorded_at':utcnow().isoformat(),'audit_event_id':uid(),**details}
    db.add(AuditEvent(id=marker['audit_event_id'],organization_id=organization_id,facility_id=facility_id,actor_id=actor.user_id,domain='D38',entity_id=run.id,action=action,details={'marker_key':key,'marker_sha256':digest(marker)}))
    container={**(_container(run,kind) or {}),key:marker}
    if kind=='assistant':run.provider=container
    else:run.provenance=container
    db.flush()
    return marker

def _verified_marker(db,run,kind,key,action):
    marker=(_container(run,kind) or {}).get(key)
    if not isinstance(marker,dict) or marker.get('version')!=1 or marker.get('run_kind')!=kind or marker.get('run_id')!=run.id or marker.get('attempt_binding')!=_binding(run,kind):return None
    event_id=marker.get('audit_event_id')
    if not isinstance(event_id,str):return None
    event=db.get(AuditEvent,event_id)
    if not event or event.action!=action or event.domain!='D38' or event.entity_id!=run.id or event.actor_id!=marker.get('actor_id') or (event.organization_id,event.facility_id)!=_scope(db,run,kind) or event.details!={'marker_key':key,'marker_sha256':digest(marker)}:return None
    return marker

def record_positive_terminal(db,run,kind,actor,result):
    """Only trusted adapter boundaries may report verified success/abstention."""
    if result.get('outcome') not in ('success','abstained'):return None
    return _write_marker(db,run,kind,actor,'positive_terminal_evidence','inference_provider_terminal_observed',{'outcome':result['outcome'],'provenance_sha256':digest(result.get('provenance',{}))})

def admission_status(db,run,kind,now=None):
    now=now if now is not None else utcnow()
    data=_container(run,kind) or {};state=run.execution_state if kind=='assistant' else run.outcome
    if kind=='assistant':
        expires=run.lease_expires_at;unknown_reason=data.get('provider_reason') in ASSISTANT_UNKNOWN or (state=='failed' and run.error in ASSISTANT_UNKNOWN)
    else:
        expires=run.created_at+timedelta(seconds=int((run.context_snapshot or {}).get('lease_seconds',360)));unknown_reason=data.get('provider_reason') in LEGACY_UNKNOWN or (state=='failed' and run.reason in LEGACY_UNKNOWN)
    result={'state':'clear','reason':None,'reconciliation':None,'positive_terminal_evidence':None}
    if state=='running' and expires and expires>now:return {**result,'state':'active','reason':'RUNNING'}
    unknown=state in ('running','timeout','interrupted') or data.get('provider_outcome') in ('timeout','interrupted') or unknown_reason
    if not unknown:return result
    terminal=_verified_marker(db,run,kind,'positive_terminal_evidence','inference_provider_terminal_observed')
    if terminal and terminal.get('outcome') in ('success','abstained'):return {**result,'reason':'VERIFIED_PROVIDER_TERMINAL','positive_terminal_evidence':terminal}
    reconciled=_verified_marker(db,run,kind,'operator_reconciliation','inference_unknown_reconciled')
    if reconciled and reconciled.get('acknowledgement')==ACKNOWLEDGEMENT:return {**result,'reason':'OPERATOR_RECONCILED','reconciliation':reconciled}
    return {**result,'state':'quarantined','reason':'REMOTE_EXECUTION_UNKNOWN'}

def reconcile_unknown_inference(db,operator,*,kind,run_id,acknowledgement,evidence_reference,workers_quiesced,provider_drained):
    """Private operator function; caller owns transaction. Never expose as HTTP.

    Stop all HIS dispatchers; independently establish provider drain/completion/
    cancellation and retain evidence first. Supply an active persisted identity
    admin Actor and exact acknowledgement. This function performs no host work.
    """
    from .auth import revalidate_actor,require
    from .assistant_admission import lock_admission
    revalidate_actor(db,operator);require(operator,'identity.admin');require(operator,'D38.write')
    if acknowledgement!=ACKNOWLEDGEMENT or workers_quiesced is not True or provider_drained is not True or not isinstance(evidence_reference,str) or not evidence_reference.strip() or len(evidence_reference)>240:raise HTTPException(422,detail={'code':'EXPLICIT_INFERENCE_RECONCILIATION_REQUIRED'})
    if kind not in ('assistant','legacy'):raise HTTPException(422,detail={'code':'UNKNOWN_INFERENCE_KIND'})
    lock_admission(db)
    run=db.get(AssistantRun if kind=='assistant' else InferenceRun,run_id,with_for_update=True)
    if not run or _scope(db,run,kind)!=(operator.organization_id,operator.facility_id):raise HTTPException(404,detail={'code':'INFERENCE_RECONCILIATION_NOT_FOUND'})
    status=admission_status(db,run,kind)
    if status['reason']=='OPERATOR_RECONCILED':return status['reconciliation']
    if status['state']!='quarantined':raise HTTPException(409,detail={'code':'INFERENCE_NOT_QUARANTINED'})
    if kind=='assistant' and run.execution_state=='running':
        run.execution_state='interrupted';run.review_state='unavailable';run.completed_at=utcnow()
        if not run.error:run.error='OPERATOR_RECONCILED_REMOTE_UNKNOWN'
    elif kind=='legacy' and run.outcome=='running':
        run.outcome='interrupted';run.completed_at=utcnow()
        if not run.reason:run.reason='OPERATOR_RECONCILED_REMOTE_UNKNOWN'
    return _write_marker(db,run,kind,operator,'operator_reconciliation','inference_unknown_reconciled',{'acknowledgement':acknowledgement,'evidence_reference':evidence_reference.strip(),'workers_quiesced':True,'provider_drained':True,'prior_state':status['state']})
