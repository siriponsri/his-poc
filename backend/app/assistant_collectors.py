"""Permission-specific source packets, stable freshness and generated-output exclusion."""
from sqlalchemy import select
from . import models as M
from .models_clinical import LabRequest, Handover
from .models_assistant import AssistantEffect
from .common import digest, canonical
from .core import bound, scope_query
from .assistant_profiles import require_profile, allowed_effects

VIEW_BYTES = 2000  # Complete canonical view; leaves >=816 bytes for pinned system/profile text.
MAX_INCLUDED_SOURCES = 12  # Frozen draft/effect source reference cardinality.

def _pristine(db, row, kind):
    column = AssistantEffect.document_id if kind == 'document' else AssistantEffect.task_id
    for effect in db.scalars(select(AssistantEffect).where(column == row.id)):
        receipt = effect.receipt
        if not receipt.get('created'):
            continue
        if kind == 'document':
            attested = db.scalar(select(M.DocumentAttestation.id).where(M.DocumentAttestation.document_version_id == row.current_version_id))
            # Merely moving an unchanged generated draft into review does not make
            # its model text a new clinical source. Require a human revision or attestation.
            if row.current_version_id == receipt.get('document_version_id') and not attested:
                return True
        elif row.version == receipt.get('version') and row.status == receipt.get('status') and row.title == receipt.get('title'):
            return True
    return False

def collect_packet(db, actor, profile, patient_id, encounter_id, locale='th'):
    definition = require_profile(actor, profile)
    patient, encounter = bound(db,actor,patient_id,encounter_id)
    rows = []
    def add(kind, identity, version, fields, text=None, label=None):
        item = {'kind':kind,'id':identity,'version':version,'fields':fields,'label':label or kind}
        if text is not None:
            item['text'] = text
        rows.append(item)
    # DOB is stable source evidence; advancing time alone must not trigger inference.
    pfields={'display_name':patient.display_name,'sex':patient.sex,'birth_date':patient.birth_date.isoformat() if patient.birth_date else None}
    add('patient',patient.id,patient.version,pfields,label=patient.display_name)
    add('encounter',encounter.id,encounter.version,{'kind':encounter.kind,'status':encounter.status},label='Current visit')
    unavailable=[]
    if profile != 'laboratory_handoff':
        docs=db.scalars(scope_query(M.Document,actor).where(M.Document.patient_id==patient.id,M.Document.encounter_id==encounter.id).order_by(M.Document.created_at.desc(),M.Document.id)).all()
        for doc in docs:
            if _pristine(db,doc,'document'):
                continue
            # Records must not SELECT revision content or created_by, even for counting.
            revision=db.execute(select(M.DocumentVersion.id,M.DocumentVersion.content_hash).where(M.DocumentVersion.id==doc.current_version_id)).first()
            fields={'title':doc.title,'status':doc.status,'version':doc.version,'revision':revision.id if revision else None,'content_hash':revision.content_hash if revision else None}
            text=None
            if profile != 'records_readiness' and revision:
                text=db.scalar(select(M.DocumentVersion.content).where(M.DocumentVersion.id==revision.id))
            add('document',doc.id,doc.version,fields,text,doc.title)
    if profile == 'nursing_handover':
        for h in db.scalars(scope_query(Handover,actor).where(Handover.patient_id==patient.id,Handover.encounter_id==encounter.id).order_by(Handover.created_at.desc(),Handover.id)):
            add('handover',h.id,h.version,{'status':h.status,'summary':h.summary,'pending_tasks':h.pending_tasks},label='Nursing handover')
    if profile == 'laboratory_handoff' or (profile=='visit_preparation' and 'D10.read' in actor.permissions):
        for lab in db.scalars(scope_query(LabRequest,actor).where(LabRequest.patient_id==patient.id,LabRequest.encounter_id==encounter.id,LabRequest.status.in_(['released','corrected'])).order_by(LabRequest.created_at.desc(),LabRequest.id)):
            result=f'{lab.analyte}: {lab.result_value or ""} {lab.unit or ""} ({lab.reference_range or ""})'
            add('lab',lab.id,lab.version,{'analyte':lab.analyte,'result_value':lab.result_value,'unit':lab.unit,'reference_range':lab.reference_range,'result':result,'status':lab.status,'critical':lab.critical},label=lab.analyte)
    elif profile=='visit_preparation':
        unavailable.append('D10')
    task_domains=[d for d in definition['domains'] if d+'.read' in actor.permissions]
    for task in db.scalars(scope_query(M.Task,actor).where(M.Task.patient_id==patient.id,M.Task.encounter_id==encounter.id,M.Task.domain.in_(task_domains)).order_by(M.Task.created_at.desc(),M.Task.id)):
        if not _pristine(db,task,'task'):
            add('task',task.id,task.version,{'domain':task.domain,'kind':task.kind,'title':task.title,'status':task.status},label=task.title)
    source_digest=digest({'profile':profile,'sources':rows,'unavailable_domains':unavailable})
    included=[]
    def make_view(sources):
        refs=[s['ref'] for s in sources]
        effects=[]
        for kind in allowed_effects(actor,profile):
            candidate={'action_id':f'a{len(effects)+1}','kind':kind,'source_refs':refs}
            if kind=='create_visit_draft':candidate['draft_id']='visit'
            if kind=='create_nursing_draft':candidate['draft_id']='handover'
            effects.append(candidate)
        coverage={'eligible_sources':len(rows),'included_sources':len(sources),'omitted_sources':len(rows)-len(sources),'unavailable_domains':unavailable}
        return {'profile':profile,'locale':locale,'sources':sources,'coverage':coverage,'effect_candidates':effects}
    for row in rows:
        fields=dict(row['fields'])
        if row['kind']=='document':
            fields={k:fields[k] for k in ('title','status','version')}
        if row['kind']=='lab':
            fields={k:fields[k] for k in ('result','status','critical')}
        item={'ref':f's{len(included)+1}','kind':row['kind'],'fields':fields}
        if 'text' in row:
            item['text']=row['text']
        # Complete source or explicit omission. Never truncate a clinical note.
        if len(included)<MAX_INCLUDED_SOURCES and len(canonical(make_view(included+[item])).encode('utf-8')) <= VIEW_BYTES:
            included.append(item)
            row['ref']=item['ref']
    view=make_view(included)
    manifest={'sources':rows,'coverage':view['coverage'],'patient_label':patient.display_name,'patient_reference':patient.id}
    return {'source_digest':source_digest,'manifest':manifest,'view':view,'input_hash':digest(view)}

def eligible_contexts(db, actor, profile):
    require_profile(actor,profile)
    encounters=db.scalars(scope_query(M.Encounter,actor).where(M.Encounter.status!='closed').order_by(M.Encounter.created_at.desc(),M.Encounter.id).limit(100))
    return [{'patient_id':e.patient_id,'encounter_id':e.id,'patient_label':db.get(M.Patient,e.patient_id).display_name,'patient_reference':e.patient_id,'profile':profile} for e in encounters]
