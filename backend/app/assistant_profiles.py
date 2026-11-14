"""Frozen profile capabilities. Availability derives only from persisted permissions."""
from fastapi import HTTPException

PROFILES = {
    'visit_preparation': {'label':'Visit preparation','permissions':{'D37.write','D03.read','D22.read','documents.content'}, 'domains':('D37','D22'), 'effects':('create_visit_draft','create_document_review_task')},
    'nursing_handover': {'label':'Nursing handover','permissions':{'D06.read','D06.write','D03.read','D22.read','documents.content'}, 'domains':('D06','D22'), 'effects':('create_nursing_draft','create_nursing_followup_task')},
    'records_readiness': {'label':'Records readiness','permissions':{'D01.write','D03.read','D22.read'}, 'domains':('D01','D22'), 'effects':('create_records_review_task',)},
    'laboratory_handoff': {'label':'Laboratory handoff','permissions':{'D10.read','D10.write','D07.read','D03.read'}, 'domains':('D10',), 'effects':('link_lab_review_task',)},
}
LIMITS = {'maximum_contexts':6,'maximum_active_watches':6,'maximum_queued_runs':6,'watch_minutes':30,'scan_seconds':30,'minimum_run_interval_seconds':60,'maximum_auto_runs':3,'maximum_active_inferences':1}

def available(actor, profile):
    return profile in PROFILES and not actor.patient_scope and PROFILES[profile]['permissions'] <= actor.permissions

def require_profile(actor, profile):
    if profile not in PROFILES:
        raise HTTPException(422,detail={'code':'UNKNOWN_ASSISTANT_PROFILE'})
    if not available(actor,profile):
        raise HTTPException(403,detail={'code':'ASSISTANT_PROFILE_FORBIDDEN'})
    return PROFILES[profile]

def allowed_effects(actor,profile):
    if not available(actor,profile):return []
    return [kind for kind in PROFILES[profile]['effects'] if kind not in ('create_visit_draft','create_nursing_draft') or {'D22.write','documents.content'} <= actor.permissions]
