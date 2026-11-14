"""One transaction: reviewed revision, decision, ordinary domain drafts/tasks, receipt."""
from copy import deepcopy
from fastapi import HTTPException
from sqlalchemy import select
from .models import Task
from .models_assistant import AssistantRevision, AssistantDecision, AssistantEffect
from .assistant_core import scoped_run, run_dto, effect_dto, actor_fence
from .assistant_profiles import PROFILES
from .common import digest, uid, authorization_hash, audit
from .core import create_document, create_task, DocumentInput, TaskInput, scope_query
from .auth import require_domain

TASKS={
    'create_document_review_task':('D37','document_review','Review visit documentation'),
    'create_nursing_followup_task':('D06','nursing_followup','Review nursing handover and follow-up'),
    'create_records_review_task':('D01','records_review','Review patient and visit document metadata'),
    'link_lab_review_task':('D10','labclear_review','Review released laboratory results'),
}

def apply_run(db,actor,run_id,body):
    actor_fence(db,actor)
    run,packet=scoped_run(db,actor,run_id,True)
    encounter=next(s for s in packet['manifest']['sources'] if s['kind']=='encounter')
    if encounter['fields']['status'] in ('closed','completed','discharged','cancelled'):
        raise HTTPException(409,detail={'code':'ASSISTANT_CONTEXT_CLOSED'})
    revision=db.scalar(select(AssistantRevision).where(AssistantRevision.run_id==run.id).order_by(AssistantRevision.version.desc()))
    if not revision or run.execution_state!='succeeded':raise HTTPException(409,detail={'code':'ASSISTANT_REVIEW_UNAVAILABLE'})
    if (revision.id!=body.expected_revision_id or revision.version!=body.expected_version or revision.content_hash!=body.expected_content_hash or run.source_digest!=body.expected_source_digest or packet['source_digest']!=run.source_digest):
        raise HTTPException(409,detail={'code':'ASSISTANT_REVIEW_STALE'})
    if db.scalar(select(AssistantDecision.id).where(AssistantDecision.run_id==run.id)):
        raise HTTPException(409,detail={'code':'ASSISTANT_ALREADY_DECIDED'})
    candidates={c['action_id']:c for c in run.inference_view['effect_candidates']}
    suggested={c['action_id']:c for c in revision.artifact['suggested_effects']}
    if len(set(body.selected_action_ids))!=len(body.selected_action_ids) or any(action not in suggested or action not in candidates for action in body.selected_action_ids):
        raise HTTPException(422,detail={'code':'ASSISTANT_EFFECT_NOT_PROPOSED'})
    if body.decision=='rejected' and (body.selected_action_ids or body.edited_draft_text is not None):
        raise HTTPException(422,detail={'code':'REJECT_CANNOT_APPLY_EFFECTS'})
    artifact=deepcopy(revision.artifact)
    if body.edited_draft_text is not None:
        drafts=[d for d in artifact['drafts'] if any(candidates[a].get('draft_id')==d['id'] for a in body.selected_action_ids)]
        if len(drafts)!=1:raise HTTPException(422,detail={'code':'SELECT_ONE_DRAFT_TO_EDIT'})
        require_domain(actor,'D22',True)
        from .auth import require
        require(actor,'documents.content')
        drafts[0]['text']=body.edited_draft_text
        revision=AssistantRevision(id=uid(),run_id=run.id,version=revision.version+1,content_hash=digest(artifact),source_digest=run.source_digest,artifact=artifact,origin='human',created_by=actor.user_id)
        db.add(revision);db.flush()
    decision=AssistantDecision(id=uid(),run_id=run.id,revision_id=revision.id,actor_id=actor.user_id,authorization_hash=authorization_hash(actor),content_hash=revision.content_hash,decision=body.decision,selected_action_ids=body.selected_action_ids)
    db.add(decision)
    db.flush()
    effects=[]
    for action_id in body.selected_action_ids:
        candidate=candidates[action_id]
        kind=candidate['kind']
        effect=AssistantEffect(id=uid(),run_id=run.id,revision_id=revision.id,action_id=action_id,kind=kind,receipt={})
        if kind in ('create_visit_draft','create_nursing_draft'):
            draft=next((d for d in artifact['drafts'] if d['id']==candidate.get('draft_id')),None)
            if not draft:raise HTTPException(422,detail={'code':'ASSISTANT_DRAFT_MISSING'})
            title='Visit preparation' if kind=='create_visit_draft' else 'Nursing handover'
            result=create_document(DocumentInput(patient_id=run.patient_id,encounter_id=run.encounter_id,title=title,content=draft['text']),actor,db,'assistant-doc:'+effect.id)
            effect.document_id=result['id']
            effect.receipt={'domain':'D22','created':True,'document_version_id':result['current_version_id'],'version':result['version'],'content_hash':result['content_hash'],'status':'draft','origin':revision.origin}
        elif kind in TASKS:
            domain,task_kind,title=TASKS[kind]
            require_domain(actor,domain,True)
            existing=db.scalar(scope_query(Task,actor).where(Task.patient_id==run.patient_id,Task.encounter_id==run.encounter_id,Task.domain==domain,Task.kind==task_kind,Task.status.in_(['open','in_progress'])).order_by(Task.created_at,Task.id).with_for_update())
            if existing:
                effect.task_id=existing.id;effect.receipt={'domain':domain,'created':False,'version':existing.version,'status':existing.status,'title':existing.title}
            else:
                result=create_task(TaskInput(patient_id=run.patient_id,encounter_id=run.encounter_id,domain=domain,kind=task_kind,title=title),actor,db,'assistant-task:'+effect.id)
                effect.task_id=result['id'];effect.receipt={'domain':domain,'created':True,'version':result['version'],'status':result['status'],'title':result['title']}
        else:raise HTTPException(422,detail={'code':'ASSISTANT_EFFECT_FORBIDDEN'})
        db.add(effect);db.flush();effects.append(effect_dto(effect))
    run.review_state=body.decision
    audit(db,actor,PROFILES[run.profile]['domains'][0],run.id,'assistant_'+body.decision,{'decision_id':decision.id,'revision_id':revision.id,'content_hash':revision.content_hash,'selected_action_ids':body.selected_action_ids,'origin':revision.origin})
    db.flush()
    return {'run':run_dto(db,actor,run),'effects':effects,'decision_id':decision.id}
