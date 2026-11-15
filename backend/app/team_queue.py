"""Accountability for existing tasks; never advances a clinical/domain workflow."""
from datetime import timezone
from types import SimpleNamespace
from typing import Literal

from fastapi import APIRouter,Depends,Header,HTTPException,Query
from pydantic import AwareDatetime,Field
from sqlalchemy import func,or_,select

from .auth import DTO,actor_for,current_actor,revalidate_actor,require_domain
from .common import audit,begin_operation,check_version,finish_operation,serialize,utcnow
from .core import bound,scope_query
from .db import get_db
from .models import Membership,Patient,Task,TaskCoordination,User

router=APIRouter(prefix='/team-queue',tags=['accountable work'])
ACTIVE=('open','in_progress')
Domain=Query(default=None,pattern=r'^D(0[1-9]|[12][0-9]|3[0-8])$')
_MISSING=object()


class VersionInput(DTO):
    version:int=Field(strict=True,ge=1)


class AssignmentInput(VersionInput):
    assignee_id:str=Field(min_length=1,max_length=64)
    reason:str=Field(min_length=1,max_length=2000)


class ScheduleInput(VersionInput):
    due_at:AwareDatetime|None
    priority:Literal['low','normal','high']


class EscalationInput(VersionInput):
    reason:str=Field(min_length=1,max_length=2000)


def _fail(code,status=409):
    raise HTTPException(status,detail={'code':code,'outcome':'not_written'})


def _staff(actor):
    if actor.patient_scope:_fail('TEAM_QUEUE_STAFF_ONLY',403)


def _task(db,actor,identity,*,lock=False):
    _staff(actor)
    query=scope_query(Task,actor).where(Task.id==identity)
    if lock:query=query.with_for_update()
    task=db.scalar(query.execution_options(populate_existing=True))
    if task is None:_fail('NOT_FOUND',404)
    require_domain(actor,task.domain)
    return task


def _coordination(db,task):
    return db.get(TaskCoordination,task.id)


def _overdue(task,coord,observed):
    return bool(task.status in ACTIVE and coord is not None and coord.due_at is not None and coord.due_at<observed)


def _capabilities(actor,task,coord,observed):
    writable=not actor.patient_scope and task.status in ACTIVE and task.domain+'.write' in actor.permissions
    return {
        'claim':bool(writable and task.assignee_id in (None,actor.user_id)),
        'release':bool(writable and task.assignee_id==actor.user_id),
        'assign':bool(writable),'schedule':bool(writable),
        'escalate':bool(writable and _overdue(task,coord,observed) and coord.escalation_level<3),
    }


def _owners(db,actor,identities):
    if not identities:return {}
    rows=db.execute(select(User.id,User.display_name,User.username).where(
        User.id.in_(identities),User.organization_id==actor.organization_id,
    )).mappings()
    return {row['id']:dict(row) for row in rows}


def _item(db,actor,task,*,coord=_MISSING,patient_label=None,owners=None,observed=None):
    observed=observed or utcnow()
    if coord is _MISSING:coord=_coordination(db,task)
    if patient_label is None:
        patient_label=db.scalar(select(Patient.display_name).where(Patient.id==task.patient_id,
            Patient.organization_id==actor.organization_id,Patient.facility_id==actor.facility_id))
    if owners is None:owners=_owners(db,actor,[task.assignee_id] if task.assignee_id else [])
    return {
        **serialize(task),'patient_label':patient_label,
        'assignee':owners.get(task.assignee_id) if task.assignee_id else None,
        'due_at':coord.due_at.isoformat() if coord is not None and coord.due_at is not None else None,
        'priority':coord.priority if coord is not None else 'normal',
        'escalation_level':coord.escalation_level if coord is not None else 0,
        'escalation_reason':coord.escalation_reason if coord is not None else None,
        'escalated_at':coord.escalated_at.isoformat() if coord is not None and coord.escalated_at is not None else None,
        'overdue':_overdue(task,coord,observed),'capabilities':_capabilities(actor,task,coord,observed),
    }


def _eligible(db,actor,task,person):
    # The transient object only evaluates persisted grants/scope. It is never a
    # session, authorizes no caller, and is never passed to a mutation fence.
    if person.organization_id!=actor.organization_id or person.status!='active':return False
    try:
        candidate=actor_for(db,person,SimpleNamespace(id='eligibility:'+person.id,
            user_id=person.id,facility_id=actor.facility_id))
        if candidate.patient_scope:return False
        require_domain(candidate,task.domain);require_domain(candidate,task.domain,True)
        bound(db,candidate,task.patient_id,task.encounter_id)
    except HTTPException:return False
    return True


def _people_query(actor):
    return select(User.id,User.display_name,User.username,User.organization_id,User.status).join(
        Membership,Membership.user_id==User.id,
    ).where(User.organization_id==actor.organization_id,User.status=='active',
        Membership.facility_id==actor.facility_id,Membership.active.is_(True)).distinct()


def _recipient(db,actor,task,identity):
    row=db.execute(_people_query(actor).where(User.id==identity)).mappings().first()
    if row is None or not _eligible(db,actor,task,SimpleNamespace(**row)):
        _fail('TEAM_QUEUE_ASSIGNEE_UNAVAILABLE',404)
    return row


@router.get('')
def worklist(q:str=Query(default='',max_length=100),domain:str|None=Domain,
             view:Literal['all','mine','unassigned']='all',
             status:Literal['active','open','in_progress','completed','cancelled','all']='active',
             offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=50),
             actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    _staff(actor)
    if domain:require_domain(actor,domain)
    observed=utcnow()
    allowed=[permission[:3] for permission in actor.permissions if permission.endswith('.read')]
    query=scope_query(Task,actor).where(Task.domain.in_(allowed)).join(Patient,Patient.id==Task.patient_id).outerjoin(
        TaskCoordination,TaskCoordination.task_id==Task.id,
    )
    if domain:query=query.where(Task.domain==domain)
    if q.strip():
        literal=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        pattern='%'+literal+'%'
        query=query.where(or_(Task.title.ilike(pattern,escape='\\'),Task.kind.ilike(pattern,escape='\\'),Patient.display_name.ilike(pattern,escape='\\')))
    # Counts deliberately precede view/status filtering and never count hidden work.
    active=query.where(Task.status.in_(ACTIVE))
    values=db.execute(active.with_only_columns(
        func.count(Task.id),func.count(Task.id).filter(Task.assignee_id==actor.user_id),
        func.count(Task.id).filter(Task.assignee_id.is_(None)),
        func.count(Task.id).filter(TaskCoordination.due_at<observed),
        func.count(Task.id).filter(TaskCoordination.escalation_level>0),
        maintain_column_froms=True,
    )).one()
    if view=='mine':query=query.where(Task.assignee_id==actor.user_id)
    elif view=='unassigned':query=query.where(Task.assignee_id.is_(None))
    if status=='active':query=query.where(Task.status.in_(ACTIVE))
    elif status!='all':query=query.where(Task.status==status)
    total=db.scalar(query.with_only_columns(func.count(Task.id),maintain_column_froms=True))
    rows=db.execute(query.add_columns(Patient.display_name.label('patient_label'),TaskCoordination).order_by(
        Task.created_at,Task.id,
    ).offset(offset).limit(limit)).all()
    owners=_owners(db,actor,{task.assignee_id for task,_,_ in rows if task.assignee_id})
    return {'items':[_item(db,actor,task,coord=coord,patient_label=label,owners=owners,observed=observed) for task,label,coord in rows],
        'total':total,'offset':offset,'limit':limit,'scope':'authorized_work','observed_at':observed.isoformat(),
        'counts':dict(zip(('active','mine','unassigned','overdue','escalated'),values)),'counts_scope':'authorized_active_work'}


@router.get('/tasks/{id}')
def detail(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    return _item(db,actor,_task(db,actor,id))


@router.get('/tasks/{id}/assignees')
def assignees(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    task=_task(db,actor,id);items=[]
    for row in db.execute(_people_query(actor).order_by(User.username,User.id)).mappings():
        if _eligible(db,actor,task,SimpleNamespace(**row)):
            items.append({key:row[key] for key in ('id','display_name','username')})
    return {'items':items}


def _mutate(db,actor,identity,body,key,action):
    revalidate_actor(db,actor)
    task=_task(db,actor,identity,lock=True);require_domain(actor,task.domain,True)
    bound(db,actor,task.patient_id,task.encounter_id)
    if task.status not in ACTIVE:_fail('TEAM_QUEUE_TASK_TERMINAL')
    coord=_coordination(db,task)
    if task.version-(coord.operational_updates if coord is not None else 0)<1:
        _fail('TASK_OPERATIONAL_VERSION_INVALID')
    if action=='assign':_recipient(db,actor,task,body.assignee_id)
    payload=body.model_dump(mode='json')
    due=body.due_at.astimezone(timezone.utc) if action=='schedule' and body.due_at is not None else None
    if action=='schedule':payload['due_at']=due.isoformat() if due is not None else None
    operation='team_queue.'+action+':'+identity
    old=begin_operation(db,actor,key,operation,payload)
    if old is not None:return old
    check_version(task,body.version)
    observed=utcnow()
    if action=='claim' and task.assignee_id not in (None,actor.user_id):_fail('TEAM_QUEUE_ALREADY_ASSIGNED')
    if action=='release' and task.assignee_id!=actor.user_id:_fail('TEAM_QUEUE_NOT_OWNER')
    if action=='escalate':
        if not _overdue(task,coord,observed):_fail('TEAM_QUEUE_NOT_OVERDUE')
        if coord.escalation_level>=3:_fail('TEAM_QUEUE_ESCALATION_LIMIT')
    before={'assignee_id':task.assignee_id,'version':task.version,
        'due_at':coord.due_at.isoformat() if coord is not None and coord.due_at else None,
        'priority':coord.priority if coord is not None else 'normal',
        'escalation_level':coord.escalation_level if coord is not None else 0}
    if coord is None:
        coord=TaskCoordination(task_id=task.id,priority='normal',escalation_level=0,operational_updates=0)
        db.add(coord)
    if action=='claim':task.assignee_id=actor.user_id
    elif action=='release':task.assignee_id=None
    elif action=='assign':task.assignee_id=body.assignee_id
    elif action=='schedule':coord.due_at=due;coord.priority=body.priority
    elif action=='escalate':
        coord.escalation_level+=1;coord.escalation_reason=body.reason;coord.escalated_at=observed
    task.version+=1;coord.operational_updates+=1;db.flush()
    response=_item(db,actor,task,coord=coord,observed=observed)
    audit(db,actor,task.domain,task.id,'task_'+action,{'before':before,
        'after':{key:response[key] for key in ('assignee_id','version','due_at','priority','escalation_level')},
        'reason':getattr(body,'reason',None),'operational_update':True})
    return finish_operation(db,actor,key,operation,payload,response)


@router.post('/tasks/{id}/claim')
def claim(id:str,body:VersionInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    return _mutate(db,actor,id,body,key,'claim')


@router.post('/tasks/{id}/release')
def release(id:str,body:VersionInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    return _mutate(db,actor,id,body,key,'release')


@router.post('/tasks/{id}/assign')
def assign(id:str,body:AssignmentInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    return _mutate(db,actor,id,body,key,'assign')


@router.post('/tasks/{id}/schedule')
def schedule(id:str,body:ScheduleInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    return _mutate(db,actor,id,body,key,'schedule')


@router.post('/tasks/{id}/escalate')
def escalate(id:str,body:EscalationInput,actor=Depends(current_actor),db=Depends(get_db,scope='function'),key:str=Header(alias='Idempotency-Key')):
    return _mutate(db,actor,id,body,key,'escalate')
