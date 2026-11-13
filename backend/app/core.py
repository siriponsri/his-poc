"""Patient, encounter, task, order and immutable document services."""
from datetime import date
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import Field
from sqlalchemy import select,func,or_
from .db import get_db
from .auth import current_actor,revalidate_actor,require_domain,require,scoped_patient,scoped_encounter,DTO
from .models import *
from .common import serialize,audit,check_version,transition,begin_operation,finish_operation,text_hash,uid,utcnow,authorization_hash
router=APIRouter(tags=['shared-core'])
class PatientInput(DTO):
    display_name:str=Field(min_length=1,max_length=200)
    birth_date:date|None=None
    sex:Literal['female','male','other','unknown']='unknown'
    identifier:str=Field(min_length=1,max_length=120)
    issuer:str=Field(default='LOCAL',min_length=1,max_length=80)
class PatientEdit(DTO):
    version:int=Field(ge=1,strict=True)
    display_name:str=Field(min_length=1,max_length=200)
    birth_date:date|None=None
    sex:Literal['female','male','other','unknown']='unknown'
class Transition(DTO):
    version:int=Field(ge=1,strict=True)
    target:str=Field(min_length=1,max_length=32)
    reason:str|None=Field(default=None,max_length=2000)
    acknowledge_pending:bool=False
class EncounterInput(DTO):
    patient_id:str
    department_id:str|None=None
    kind:Literal['OPD','IPD','ER']='OPD'
class TaskInput(DTO):
    patient_id:str
    encounter_id:str
    domain:str=Field(pattern=r'^D(0[1-9]|[12][0-9]|3[0-8])$')
    kind:str=Field(min_length=1,max_length=64)
    title:str=Field(min_length=1,max_length=240)
class DocumentInput(DTO):
    patient_id:str
    encounter_id:str
    title:str=Field(min_length=1,max_length=240)
    content:str=Field(min_length=1,max_length=100000)
class DocumentEdit(DTO):
    version:int=Field(ge=1,strict=True)
    content:str=Field(min_length=1,max_length=100000)
    reason:str=Field(min_length=1,max_length=2000)
class DocumentTransition(Transition):content_hash:str=Field(min_length=64,max_length=64)
class OrderInput(DTO):
    patient_id:str
    encounter_id:str
    kind:Literal['lab','medication','imaging','procedure','rehab']
    code:str=Field(min_length=1,max_length=80)
    label:str=Field(min_length=1,max_length=240)
    instructions:str=Field(default='',max_length=5000)
    quantity:Decimal=Field(default=Decimal('1'),gt=0,max_digits=18,decimal_places=3)
    unit:str=Field(default='unit',min_length=1,max_length=40)
class OrderEdit(DTO):
    version:int=Field(ge=1,strict=True)
    instructions:str=Field(min_length=1,max_length=5000)

def scope_query(model,actor):
    q=select(model).where(model.organization_id==actor.organization_id,model.facility_id==actor.facility_id)
    if actor.patient_scope:q=q.where(model.patient_id==actor.patient_scope if hasattr(model,'patient_id') else model.id==actor.patient_scope)
    if actor.care_patient_ids is not None:q=q.where((model.patient_id if hasattr(model,'patient_id') else model.id).in_(actor.care_patient_ids))
    return q

def bound(db,actor,patient_id,encounter_id,lock=False):
    p=scoped_patient(db,actor,patient_id,lock);e=scoped_encounter(db,actor,encounter_id,lock)
    if e.patient_id!=p.id:raise HTTPException(404,detail={'code':'CONTEXT_NOT_FOUND'})
    return p,e

def record(db,actor,model,id,lock=False):
    q=scope_query(model,actor).where(model.id==id)
    r=db.scalar(q.with_for_update() if lock else q)
    if not r:raise HTTPException(404,detail={'code':'NOT_FOUND'})
    return r

def start(db,actor,domain,key,operation,payload):
    revalidate_actor(db,actor);require_domain(actor,domain,True)
    return begin_operation(db,actor,key,operation,payload)

def saved(db,actor,key,operation,payload,item,domain,action):
    db.flush();result=serialize(item);audit(db,actor,domain,item.id,action,{'version':getattr(item,'version',None)})
    return finish_operation(db,actor,key,operation,payload,result)

def document_dto(db,d,actor=None):
    value=serialize(d);v=db.get(DocumentVersion,d.current_version_id) if d.current_version_id else None
    value['content']=v.content if v and (actor is None or 'documents.content' in actor.permissions) else None;value['content_hash']=v.content_hash if v else None
    value['content_access']='allowed' if actor is None or 'documents.content' in actor.permissions else 'metadata_only'
    return value
@router.get('/patients')
def patients(q:str='',actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D01');query=scope_query(Patient,actor)
    if q:query=query.where(Patient.display_name.ilike('%'+q[:100]+'%'))
    return {'items':[serialize(p) for p in db.scalars(query.order_by(Patient.created_at).limit(200))]}
@router.get('/patients/{id}')
def patient(id:str,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D01');p=scoped_patient(db,actor,id);r=serialize(p);r['identifiers']=[serialize(i) for i in db.scalars(select(PatientIdentifier).where(PatientIdentifier.patient_id==id))];return r
@router.post('/patients',status_code=201)
def create_patient(body:PatientInput,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    payload=body.model_dump(mode='json');op='patients.create';old=start(db,actor,'D01',key,op,payload)
    if old:return old
    if body.birth_date and body.birth_date>date.today():raise HTTPException(422,detail={'code':'BIRTH_DATE_IN_FUTURE'})
    p=Patient(id=uid(),organization_id=actor.organization_id,facility_id=actor.facility_id,display_name=body.display_name,birth_date=body.birth_date,sex=body.sex)
    db.add(p);db.flush();db.add(PatientIdentifier(patient_id=p.id,organization_id=actor.organization_id,issuer=body.issuer,value=body.identifier))
    return saved(db,actor,key,op,payload,p,'D01','registered')
@router.patch('/patients/{id}')
def edit_patient(id:str,body:PatientEdit,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='patients.edit:'+id;payload=body.model_dump(mode='json');old=start(db,actor,'D01',key,op,payload)
    if old:return old
    p=scoped_patient(db,actor,id,True);check_version(p,body.version)
    if p.status=='inactive':raise HTTPException(409,detail={'code':'PATIENT_INACTIVE'})
    if body.birth_date and body.birth_date>date.today():raise HTTPException(422,detail={'code':'BIRTH_DATE_IN_FUTURE'})
    p.display_name=body.display_name;p.birth_date=body.birth_date;p.sex=body.sex;p.version+=1
    return saved(db,actor,key,op,payload,p,'D01','demographics_amended')
@router.post('/patients/{id}/transition')
def patient_transition(id:str,body:Transition,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='patients.transition:'+id;payload=body.model_dump();old=start(db,actor,'D01',key,op,payload)
    if old:return old
    p=scoped_patient(db,actor,id,True);transition(p,body.target,{'draft':['verified'],'verified':['active'],'active':['inactive']},body.version)
    return saved(db,actor,key,op,payload,p,'D01',body.target)
@router.get('/encounters')
def encounters(patient_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D03');q=scope_query(Encounter,actor)
    if patient_id:scoped_patient(db,actor,patient_id);q=q.where(Encounter.patient_id==patient_id)
    return {'items':[serialize(x) for x in db.scalars(q.order_by(Encounter.created_at.desc()).limit(200))]}
@router.get('/encounters/{id}')
def encounter(id:str,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D03');return serialize(scoped_encounter(db,actor,id))
@router.post('/encounters',status_code=201)
def create_encounter(body:EncounterInput,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='encounters.create';payload=body.model_dump();old=start(db,actor,'D03',key,op,payload)
    if old:return old
    p=scoped_patient(db,actor,body.patient_id,True)
    if p.status!='active':raise HTTPException(409,detail={'code':'PATIENT_NOT_ACTIVE'})
    if body.department_id:
        dep=db.get(Department,body.department_id)
        if not dep or dep.facility_id!=actor.facility_id or dep.organization_id!=actor.organization_id:raise HTTPException(404,detail={'code':'DEPARTMENT_NOT_FOUND'})
    e=Encounter(organization_id=actor.organization_id,facility_id=actor.facility_id,patient_id=p.id,department_id=body.department_id,kind=body.kind);db.add(e)
    return saved(db,actor,key,op,payload,e,'D03','opened')
@router.post('/encounters/{id}/transition')
def encounter_transition(id:str,body:Transition,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='encounters.transition:'+id;payload=body.model_dump();old=start(db,actor,'D03',key,op,payload)
    if old:return old
    e=scoped_encounter(db,actor,id,True)
    if body.target in ('reviewed','completed','closed'):require(actor,'clinical.approve')
    if body.target=='closed':
        pending=db.scalar(select(func.count()).select_from(Task).where(Task.encounter_id==id,Task.status.in_(['open','in_progress'])))
        if pending and not (body.acknowledge_pending and body.reason):raise HTTPException(409,detail={'code':'PENDING_TASKS_REQUIRE_CONFIRMATION','pending_count':pending})
        e.disposition=body.reason
    transition(e,body.target,{'waiting':['in_consult'],'in_consult':['reviewed'],'reviewed':['completed'],'completed':['closed']},body.version)
    return saved(db,actor,key,op,payload,e,'D03',body.target)
@router.get('/tasks')
def tasks(encounter_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    q=scope_query(Task,actor).where(Task.domain.in_([p[:3] for p in actor.permissions if p.endswith('.read')]))
    if encounter_id:scoped_encounter(db,actor,encounter_id);q=q.where(Task.encounter_id==encounter_id)
    return {'items':[serialize(x) for x in db.scalars(q.order_by(Task.created_at.desc()).limit(200))]}
@router.post('/tasks',status_code=201)
def create_task(body:TaskInput,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='tasks.create';payload=body.model_dump();old=start(db,actor,body.domain,key,op,payload)
    if old:return old
    p,e=bound(db,actor,body.patient_id,body.encounter_id,True)
    if e.status=='closed':raise HTTPException(409,detail={'code':'ENCOUNTER_CLOSED'})
    t=Task(**payload,organization_id=actor.organization_id,facility_id=actor.facility_id);db.add(t)
    return saved(db,actor,key,op,payload,t,body.domain,'task_created')
@router.post('/tasks/{id}/transition')
def task_transition(id:str,body:Transition,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    t=record(db,actor,Task,id);op='tasks.transition:'+id;payload=body.model_dump();old=start(db,actor,t.domain,key,op,payload)
    if old:return old
    t=record(db,actor,Task,id,True)
    if db.scalar(select(ClinicalOrder.id).where(ClinicalOrder.task_id==id)):raise HTTPException(409,detail={'code':'ORDER_TASK_REQUIRES_DOMAIN_ACTION'})
    if body.target=='completed' and db.scalar(select(Proposal.id).where(Proposal.task_id==id)):raise HTTPException(409,detail={'code':'AI_TASK_REQUIRES_REVIEW_COMMIT'})
    transition(t,body.target,{'open':['in_progress','cancelled'],'in_progress':['completed','cancelled']},body.version)
    return saved(db,actor,key,op,payload,t,t.domain,body.target)
@router.get('/documents')
def documents(encounter_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D22');q=scope_query(Document,actor)
    if encounter_id:scoped_encounter(db,actor,encounter_id);q=q.where(Document.encounter_id==encounter_id)
    return {'items':[document_dto(db,d,actor) for d in db.scalars(q.order_by(Document.created_at.desc()).limit(200))]}
@router.get('/documents/{id}/versions')
def document_versions(id:str,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D22');require(actor,'documents.content');record(db,actor,Document,id)
    return {'items':[serialize(v) for v in db.scalars(select(DocumentVersion).where(DocumentVersion.document_id==id).order_by(DocumentVersion.version))]}
@router.post('/documents',status_code=201)
def create_document(body:DocumentInput,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    require(actor,'documents.content');op='documents.create';payload=body.model_dump();old=start(db,actor,'D22',key,op,payload)
    if old:return old
    require(actor,'documents.content')
    p,e=bound(db,actor,body.patient_id,body.encounter_id,True)
    if e.status=='closed':raise HTTPException(409,detail={'code':'ENCOUNTER_CLOSED'})
    d=Document(id=uid(),organization_id=actor.organization_id,facility_id=actor.facility_id,patient_id=p.id,encounter_id=e.id,title=body.title,version=1);db.add(d);db.flush()
    v=DocumentVersion(id=uid(),document_id=d.id,version=1,content=body.content,content_hash=text_hash(body.content),created_by=actor.user_id);db.add(v);db.flush();d.current_version_id=v.id
    audit(db,actor,'D22',d.id,'draft_created',{'version_id':v.id,'content_hash':v.content_hash});return finish_operation(db,actor,key,op,payload,document_dto(db,d))
@router.post('/documents/{id}/revise')
def revise_document(id:str,body:DocumentEdit,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    require(actor,'documents.content');op='documents.revise:'+id;payload=body.model_dump();old=start(db,actor,'D22',key,op,payload)
    if old:return old
    require(actor,'documents.content')
    d=record(db,actor,Document,id,True);check_version(d,body.version);prior=d.current_version_id
    if d.status=='in_review':raise HTTPException(409,detail={'code':'RETURN_BEFORE_REVISION'})
    d.version+=1;d.status='amended' if d.status=='attested' else 'draft';d.published=False
    v=DocumentVersion(id=uid(),document_id=id,version=d.version,content=body.content,content_hash=text_hash(body.content),created_by=actor.user_id,reason=body.reason);db.add(v);db.flush();d.current_version_id=v.id
    audit(db,actor,'D22',d.id,'revision_created',{'previous_version_id':prior,'version_id':v.id,'content_hash':v.content_hash});return finish_operation(db,actor,key,op,payload,document_dto(db,d))
@router.post('/documents/{id}/transition')
def document_transition(id:str,body:DocumentTransition,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='documents.transition:'+id;payload=body.model_dump();old=start(db,actor,'D22',key,op,payload)
    if old:return old
    require(actor,'documents.content')
    d=record(db,actor,Document,id,True);v=db.get(DocumentVersion,d.current_version_id);check_version(d,body.version)
    if v.content_hash!=body.content_hash:raise HTTPException(409,detail={'code':'HASH_MISMATCH'})
    if body.target=='attested':require(actor,'clinical.attest');db.add(DocumentAttestation(document_version_id=v.id,actor_id=actor.user_id,content_hash=v.content_hash))
    # Revision number identifies content; status transitions do not invent content versions.
    allowed={'draft':['in_review'],'amended':['in_review'],'in_review':['attested','returned'],'returned':['draft']}
    if body.target not in allowed.get(d.status,[]):raise HTTPException(409,detail={'code':'INVALID_TRANSITION'})
    d.status=body.target
    audit(db,actor,'D22',id,body.target,{'version_id':v.id,'content_hash':v.content_hash});return finish_operation(db,actor,key,op,payload,document_dto(db,d))
@router.get('/orders')
def orders(encounter_id:str|None=None,kind:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    require_domain(actor,'D07');q=scope_query(ClinicalOrder,actor)
    if encounter_id:scoped_encounter(db,actor,encounter_id);q=q.where(ClinicalOrder.encounter_id==encounter_id)
    if kind:q=q.where(ClinicalOrder.kind==kind)
    return {'items':[serialize(o) for o in db.scalars(q.order_by(ClinicalOrder.created_at.desc()).limit(200))]}
@router.get('/orders/catalog')
def catalog(actor=Depends(current_actor)):
    require_domain(actor,'D07');return {'items':[{'kind':k,'code':'SYN-'+k.upper(),'label':'Synthetic '+k,'source':'AUTHORED_DEMO_NO_CLINICAL_RULES'} for k in ['lab','medication','imaging','procedure','rehab']]}
@router.post('/orders',status_code=201)
def create_order(body:OrderInput,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='orders.create';payload=body.model_dump(mode='json');old=start(db,actor,'D07',key,op,payload)
    if old:return old
    require(actor,'orders.sign');p,e=bound(db,actor,body.patient_id,body.encounter_id,True)
    if e.status=='closed':raise HTTPException(409,detail={'code':'ENCOUNTER_CLOSED'})
    o=ClinicalOrder(**body.model_dump(),requester_id=actor.user_id,organization_id=actor.organization_id,facility_id=actor.facility_id);db.add(o)
    return saved(db,actor,key,op,payload,o,'D07','draft_created')
@router.post('/orders/{id}/revise')
def revise_order(id:str,body:OrderEdit,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='orders.revise:'+id;payload=body.model_dump();old=start(db,actor,'D07',key,op,payload)
    if old:return old
    require(actor,'orders.sign');o=record(db,actor,ClinicalOrder,id,True);check_version(o,body.version)
    if o.status in ('in_progress','completed','cancelled'):raise HTTPException(409,detail={'code':'ORDER_ALREADY_EXECUTING'})
    db.add(OrderRevision(order_id=id,version=o.version,instructions=o.instructions,actor_id=actor.user_id));o.version+=1;o.instructions=body.instructions;o.status='draft'
    if o.task_id:
        t=db.get(Task,o.task_id);t.status='cancelled';t.version+=1;o.task_id=None
    return saved(db,actor,key,op,payload,o,'D07','revised')
@router.post('/orders/{id}/transition')
def order_transition(id:str,body:Transition,actor=Depends(current_actor),db=Depends(get_db,scope="function"),key:str=Header(alias='Idempotency-Key')):
    op='orders.transition:'+id;payload=body.model_dump();old=start(db,actor,'D07',key,op,payload)
    if old:return old
    o=record(db,actor,ClinicalOrder,id,True);e=scoped_encounter(db,actor,o.encounter_id,True)
    if body.target=='signed':require(actor,'orders.sign')
    elif body.target=='cancelled':require(actor,'orders.sign')
    else:require_domain(actor,{'lab':'D10','medication':'D08','imaging':'D11','procedure':'D12','rehab':'D16'}[o.kind],True)
    transition(o,body.target,{'draft':['signed'],'signed':['acknowledged','cancelled'],'acknowledged':['in_progress','cancelled'],'in_progress':['completed']},body.version)
    if body.target=='signed':
        if e.status=='closed':raise HTTPException(409,detail={'code':'ENCOUNTER_CLOSED'})
        t=Task(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,encounter_id=o.encounter_id,domain={'lab':'D10','medication':'D08','imaging':'D11','procedure':'D12','rehab':'D16'}[o.kind],kind=o.kind,title=o.label);db.add(t);db.flush();o.task_id=t.id
    if o.task_id and body.target in ('cancelled','completed'):
        t=db.get(Task,o.task_id);t.status=body.target;t.version+=1
    return saved(db,actor,key,op,payload,o,'D07',body.target)
@router.get('/home')
def home(actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    allowed=[p[:3] for p in actor.permissions if p.endswith('.read')]
    q=scope_query(Task,actor).where(Task.domain.in_(allowed),Task.status.in_(['open','in_progress']))
    items=[serialize(t) for t in db.scalars(q.order_by(Task.created_at).limit(100))]
    from .domains import clinical,erp
    counts=[];worklists=[]
    terminal={'closed','completed','cancelled','discharged','rejected','disabled','inactive','revoked'}
    core_models={'D01':Patient,'D03':Encounter,'D07':ClinicalOrder,'D22':Document}
    for domain in sorted(set(allowed)):
        rows=[]
        if domain in core_models:rows=list(db.scalars(scope_query(core_models[domain],actor)))
        elif domain in clinical.SPECS:rows=list(db.scalars(clinical.scoped_query(db,actor,clinical.SPECS[domain]['model'])))
        elif domain in erp.MODELS:rows=erp.rows(db,actor,erp.MODELS[domain])
        elif domain=='D37':
            task_ids=[t.id for t in db.scalars(scope_query(Task,actor)) if t.domain+'.read' in actor.permissions]
            rows=list(db.scalars(select(Proposal).where(Proposal.task_id.in_(task_ids))))
        elif domain=='D34' and 'identity.admin' in actor.permissions:
            ids=select(Membership.user_id).where(Membership.facility_id==actor.facility_id)
            rows=list(db.scalars(select(User).where(User.id.in_(ids),User.organization_id==actor.organization_id)))
        else:continue
        pending=[row for row in rows if row.status not in terminal]
        counts.append({'domain':domain,'record_count':len(rows),'pending_count':len(pending),'href':'/domains/'+domain,'pending_states_rule':'excludes closed/completed/cancelled/discharged/rejected/disabled/inactive/revoked'})
        worklists.extend({'domain':domain,'id':row.id,'status':row.status,'href':'/domains/'+domain+'/'+row.id} for row in pending[:5])
    return {'open_tasks':len(items),'items':items,'domains':sorted(set(allowed)),'domain_counts':counts,'worklists':worklists,'source':'persisted_authorized_records','truncated':len(items)==100}
@router.get('/reference')
def reference(actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    return {'departments':[serialize(d) for d in db.scalars(select(Department).where(Department.organization_id==actor.organization_id,Department.facility_id==actor.facility_id))],'locations':[serialize(d) for d in db.scalars(select(Location).where(Location.organization_id==actor.organization_id,Location.facility_id==actor.facility_id))]}
@router.get('/audit')
def audit_list(entity_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    q=select(AuditEvent).where(AuditEvent.organization_id==actor.organization_id,AuditEvent.facility_id==actor.facility_id)
    if entity_id:
        allowed=False
        for model,domain in [(Patient,'D01'),(Encounter,'D03'),(Task,'D37'),(Document,'D22'),(ClinicalOrder,'D07')]:
            r=db.get(model,entity_id)
            if r:
                required=r.domain if isinstance(r,Task) else domain
                require_domain(actor,required);record(db,actor,model,entity_id);allowed=True;break
        if not allowed:
            for model in (Proposal,CommittedResult,InferenceRun):
                r=db.get(model,entity_id)
                if r:
                    require_domain(actor,'D37');task=record(db,actor,Task,r.task_id);require_domain(actor,task.domain);allowed=True;break
        if not allowed:
            from .domains import clinical,erp
            for domain,spec in clinical.SPECS.items():
                if db.get(spec['model'],entity_id):clinical.record(db,actor,domain,entity_id);allowed=True;break
            if not allowed:
                for domain,model in erp.MODELS.items():
                    if db.get(model,entity_id):require_domain(actor,domain);erp.get_record(db,actor,domain,entity_id);allowed=True;break
            if not allowed:
                for domain,model,_dto in erp.SUPPORT.values():
                    if db.get(model,entity_id):
                        require_domain(actor,domain);erp.scoped(db,actor,model,entity_id)
                        if not any(row.id==entity_id for row in erp.rows(db,actor,model)):raise HTTPException(404,detail={'code':'NOT_FOUND'})
                        allowed=True;break
        if not allowed and not ({'auditor','system_admin'} & actor.roles):raise HTTPException(403,detail={'code':'AUDIT_SCOPE_DENIED'})
        q=q.where(AuditEvent.entity_id==entity_id)
    elif not ({'auditor','system_admin'} & actor.roles):raise HTTPException(403,detail={'code':'AUDIT_SCOPE_REQUIRED'})
    return {'items':[serialize(x) for x in db.scalars(q.order_by(AuditEvent.created_at.desc()).limit(200))]}
@router.get('/operations/{key}')
def operation(key:str,actor=Depends(current_actor),db=Depends(get_db,scope="function")):
    o=db.get(Operation,(actor.user_id,key))
    if not o or o.organization_id!=actor.organization_id or o.facility_id!=actor.facility_id or o.authorization_hash!=authorization_hash(actor):raise HTTPException(404,detail={'code':'OPERATION_NOT_FOUND'})
    return {'operation_key':key,'operation':o.operation,'response':o.response}
@router.get('/tasks/{id}')
def task_detail(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    t=record(db,actor,Task,id);require_domain(actor,t.domain);return serialize(t)
@router.get('/documents/{id}')
def document_detail(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D22');return document_dto(db,record(db,actor,Document,id),actor)
@router.get('/orders/{id}')
def order_detail(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D07');r=serialize(record(db,actor,ClinicalOrder,id));r['revisions']=[serialize(v) for v in db.scalars(select(OrderRevision).where(OrderRevision.order_id==id).order_by(OrderRevision.version))];return r
@router.get('/facilities')
def facilities(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require(actor,'identity.admin');return {'items':[serialize(f) for f in db.scalars(select(Facility).where(Facility.organization_id==actor.organization_id))]}
@router.get('/staff-directory')
def directory(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    if actor.patient_scope:raise HTTPException(403,detail={'code':'STAFF_ONLY'})
    ids=db.scalars(select(Membership.user_id).where(Membership.facility_id==actor.facility_id,Membership.active.is_(True))).all()
    return {'items':[{'id':u.id,'display_name':u.display_name} for u in db.scalars(select(User).where(User.id.in_(ids),User.organization_id==actor.organization_id,User.status=='active'))]}
@router.get('/reference/patients')
def patient_references(q:str='',actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require(actor,'patient.reference');query=scope_query(Patient,actor)
    if q:query=query.where(Patient.display_name.ilike('%'+q[:100]+'%'))
    return {'items':[{'id':p.id,'display_name':p.display_name,'status':p.status} for p in db.scalars(query.order_by(Patient.created_at).limit(200))],'access':'minimum_reference_metadata'}
@router.get('/reference/encounters')
def encounter_references(patient_id:str|None=None,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require(actor,'encounter.reference');query=scope_query(Encounter,actor)
    if patient_id:scoped_patient(db,actor,patient_id);query=query.where(Encounter.patient_id==patient_id)
    return {'items':[{'id':e.id,'patient_id':e.patient_id,'kind':e.kind,'status':e.status,'version':e.version} for e in db.scalars(query.order_by(Encounter.created_at.desc()).limit(200))],'access':'minimum_reference_metadata'}
