"""Task accountability against a migrated, explicitly disposable PostgreSQL18."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event,func,select

assert os.getenv('HIS_TEST_DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL'),'Disposable PostgreSQL wrapper required'

from backend.app import assistant_core,assistant_provider,team_queue
from backend.app.common import authorization_hash,digest,text_hash,uid,utcnow
from backend.app.db import SessionLocal,engine
from backend.app.main import app
from backend.app.models import AuditEvent,CareAssignment,ClinicalOrder,Document,Encounter,InferenceRun,Membership,Operation,Proposal,Role,RolePermission,SessionRecord,Task,TaskCoordination,User,UserPatientScope
from backend.app.models_erp import StaffMember
from backend.app.seed import seed

if '/api/v2/team-queue' not in app.openapi()['paths']:
    app.include_router(team_queue.router,prefix='/api/v2')
    # Production main registers API routers before its final SPA/not-found routes.
    # This isolated worker does not own main.py, so place its explicit test router
    # at that same precedence instead of appending it behind the SPA fallback.
    app.router.routes.insert(0,app.router.routes.pop())
    app.openapi_schema=None


@pytest.fixture(scope='module',autouse=True)
def migrated_synthetic_database():
    assert engine.url.database=='his_test' and engine.url.host=='127.0.0.1'
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])


def person(*,role='clinician',facility='facility-demo',organization='org-demo',status='active',care='patient-001',active=True):
    identity=uid();username='queue-'+identity
    with SessionLocal.begin() as db:
        user=User(id=identity,organization_id=organization,username=username,display_name='Synthetic queue colleague',
            password_hash=db.get(User,'user-clinician').password_hash,status=status)
        db.add(user);db.flush();db.add(Membership(id=uid(),user_id=identity,facility_id=facility,role=role,active=active))
        if care:db.add(CareAssignment(user_id=identity,patient_id=care,active=True))
        if role=='patient':db.add(UserPatientScope(user_id=identity,patient_id='patient-001'))
    return {'id':identity,'username':username}


def login(user=None,*,raise_errors=True):
    client=TestClient(app,raise_server_exceptions=raise_errors)
    response=client.post('/api/v2/auth/login',json={'username':user['username'] if user else 'clinician','password':os.environ['HIS_SEED_PASSWORD']})
    assert response.status_code==200
    client.headers['X-CSRF-Token']=response.json()['csrf_token'];return client


def task(*,title=None,domain='D06',status='open',assignee=None,patient='patient-001',encounter='encounter-001',organization='org-demo',facility='facility-demo',coord=None):
    identity=uid()
    with SessionLocal.begin() as db:
        db.add(Task(id=identity,organization_id=organization,facility_id=facility,patient_id=patient,
            encounter_id=encounter,domain=domain,kind='accountability_test',title=title or 'queue-'+identity,
            status=status,assignee_id=assignee));db.flush()
        if coord is not None:db.add(TaskCoordination(task_id=identity,**coord))
    return identity


def read(client,identity):
    response=client.get('/api/v2/team-queue/tasks/'+identity);assert response.status_code==200,response.text;return response.json()


def mutate(client,identity,action,body,*,key=None,status=200):
    response=client.post('/api/v2/team-queue/tasks/'+identity+'/'+action,json=body,headers={'Idempotency-Key':key or uid()})
    assert response.status_code==status,response.text;return response


def state(identity):
    with SessionLocal() as db:
        row=db.get(Task,identity);coord=db.get(TaskCoordination,identity)
        return {'version':row.version,'owner':row.assignee_id,'status':row.status,
            'updates':coord.operational_updates if coord else 0,'level':coord.escalation_level if coord else 0,
            'coord_exists':coord is not None,
            'audits':db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.entity_id==identity,AuditEvent.action.like('task_%'))),
            'operations':db.scalar(select(func.count()).select_from(Operation).where(Operation.operation.like('team_queue.%:'+identity)))}


def test_queue_is_staff_session_scoped_and_never_grants_write_to_readers():
    identity=task()
    with TestClient(app) as anonymous:assert anonymous.get('/api/v2/team-queue').status_code==401
    portal=person(role='patient')
    with login(portal) as client:
        assert client.get('/api/v2/team-queue').status_code==403
        assert client.get('/api/v2/team-queue/tasks/'+identity).status_code==403
    with login({'username':'auditor'}) as client:
        item=read(client,identity);assert not any(item['capabilities'].values())
        mutate(client,identity,'claim',{'version':item['version']},status=403)
    assert not state(identity)['coord_exists']


def test_scoped_server_pagination_search_and_active_counts_precede_view_status():
    actor=person();other=person();prefix='queue-filter-'+uid();now=utcnow()
    mine=task(title=prefix+' mine',assignee=actor['id'],coord={'due_at':now-timedelta(hours=1),'escalation_level':1})
    task(title=prefix+' unassigned',coord={'due_at':now+timedelta(hours=1)})
    task(title=prefix+' other',assignee=other['id'],status='in_progress',coord={'due_at':now-timedelta(minutes=1)})
    completed=task(title=prefix+' completed',assignee=actor['id'],status='completed')
    task(title=prefix+' cancelled',status='cancelled')
    task(title=prefix+' hidden-patient',patient='patient-002',encounter='encounter-002')
    task(title=prefix+' hidden-branch',patient='patient-second',encounter='encounter-second',facility='facility-second')
    task(title=prefix+' hidden-org',patient='patient-other',encounter='encounter-other',organization='org-other',facility='facility-other')
    with login(actor) as client:
        response=client.get('/api/v2/team-queue',params={'q':prefix,'domain':'D06','view':'mine','status':'completed'});assert response.status_code==200
        result=response.json();assert [item['id'] for item in result['items']]==[completed]
        assert result['counts']=={'active':3,'mine':1,'unassigned':1,'overdue':2,'escalated':1}
        assert result['counts_scope']=='authorized_active_work' and result['scope']=='authorized_work'
        result=client.get('/api/v2/team-queue',params={'q':prefix,'view':'mine'}).json()
        assert [item['id'] for item in result['items']]==[mine] and result['items'][0]['assignee']['id']==actor['id']
        assert result['items'][0]['overdue'] and result['items'][0]['capabilities']['escalate']


def test_search_paginates_beyond_old_page_and_treats_wildcards_literally():
    prefix='queue-pages-'+uid()
    identities={task(title=prefix+' '+str(index)) for index in range(55)}
    with login() as client:
        first=client.get('/api/v2/team-queue',params={'q':prefix}).json()
        last=client.get('/api/v2/team-queue',params={'q':prefix,'offset':50}).json()
        assert first['total']==55 and len(first['items'])==50 and len(last['items'])==5
        assert {item['id'] for item in first['items']+last['items']}==identities
        assert not ({item['id'] for item in first['items']}&{item['id'] for item in last['items']})
        literal=task(title=prefix+' literal%text');task(title=prefix+' literalXtext')
        result=client.get('/api/v2/team-queue',params={'q':prefix+' literal%'}).json()
        assert [item['id'] for item in result['items']]==[literal]


@pytest.mark.parametrize('params',[{'limit':0},{'limit':51},{'offset':-1},{'q':'x'*101},{'domain':'D39'},{'view':'everyone'},{'status':'unknown'}])
def test_query_contract_bounds(params):
    with login() as client:assert client.get('/api/v2/team-queue',params=params).status_code==422


def test_task_detail_and_directory_hide_other_org_branch_care_and_domain():
    actor=person();hidden=[task(patient='patient-002',encounter='encounter-002'),
        task(patient='patient-second',encounter='encounter-second',facility='facility-second'),
        task(patient='patient-other',encounter='encounter-other',organization='org-other',facility='facility-other')]
    with login(actor) as client:
        for identity in hidden:
            assert client.get('/api/v2/team-queue/tasks/'+identity).status_code==404
            assert client.get('/api/v2/team-queue/tasks/'+identity+'/assignees').status_code==404
            mutate(client,identity,'claim',{'version':1},status=404)
    identity=task()
    with login({'username':'registration'}) as client:
        assert client.get('/api/v2/team-queue/tasks/'+identity).status_code==403
        assert client.get('/api/v2/team-queue',params={'domain':'D06'}).status_code==403


def test_assignee_directory_uses_current_membership_permissions_credentials_and_care():
    identity=task();eligible=person();no_care=person(care=None);suspended=person(status='suspended')
    inactive_member=person(active=False);wrong_branch=person(facility='facility-second');wrong_org=person(organization='org-other',facility='facility-other',care=None)
    portal=person(role='patient');wrong_domain=person(role='billing');expired=person()
    with SessionLocal.begin() as db:
        db.add(StaffMember(id=uid(),organization_id='org-demo',facility_id='facility-demo',user_id=expired['id'],
            department_id='department-demo',credential_status='active',credential_valid_until=date.today()-timedelta(days=1),privilege='D06.write'))
    with login() as client:
        response=client.get('/api/v2/team-queue/tasks/'+identity+'/assignees');assert response.status_code==200
        rows=response.json()['items'];ids={row['id'] for row in rows};assert eligible['id'] in ids
        assert not ids&{p['id'] for p in [no_care,suspended,inactive_member,wrong_branch,wrong_org,portal,wrong_domain,expired]}
        assert all(set(row)=={'id','display_name','username'} for row in rows)
        assert all(word not in response.text for word in ['password_hash','csrf','token'])


def test_claim_replay_and_schedule_release_increment_one_version_and_semantic_counter():
    actor=person();identity=task();key=uid()
    with login(actor) as client:
        first=mutate(client,identity,'claim',{'version':1},key=key).json()
        assert first['assignee']['id']==actor['id'] and first['status']=='open'
        assert mutate(client,identity,'claim',{'version':1},key=key).json()==first
        due=(utcnow()+timedelta(hours=1)).isoformat()
        scheduled=mutate(client,identity,'schedule',{'version':first['version'],'due_at':due,'priority':'high'}).json()
        assert scheduled['priority']=='high' and scheduled['assignee_id']==actor['id']
        release_key=uid();released=mutate(client,identity,'release',{'version':scheduled['version']},key=release_key).json()
        assert released['assignee'] is None
        assert mutate(client,identity,'release',{'version':scheduled['version']},key=release_key).json()==released
    persisted=state(identity)
    assert persisted=={'version':4,'owner':None,'status':'open','updates':3,'level':0,'coord_exists':True,'audits':3,'operations':3}
    assert persisted['version']-persisted['updates']==1


def test_two_independent_simultaneous_claims_have_one_owner_and_atomic_receipt():
    people=[person(),person()];identity=task()
    def request(actor):
        with login(actor) as client:
            response=client.post('/api/v2/team-queue/tasks/'+identity+'/claim',json={'version':1},headers={'Idempotency-Key':uid()})
            return response.status_code,response.json(),actor['id']
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(request,people))
    assert sorted(result[0] for result in results)==[200,409]
    winner=next(result for result in results if result[0]==200)
    persisted=state(identity);assert persisted['owner']==winner[2]
    assert persisted['version']==2 and persisted['updates']==persisted['audits']==persisted['operations']==1


def test_other_owner_cannot_claim_or_release_and_stale_version_does_not_write():
    owner=person();other=person();identity=task(assignee=owner['id'])
    with login(other) as client:
        mutate(client,identity,'claim',{'version':1},status=409)
        mutate(client,identity,'release',{'version':1},status=409)
    with login(owner) as client:mutate(client,identity,'release',{'version':99},status=409)
    assert state(identity)=={'version':1,'owner':owner['id'],'status':'open','updates':0,'level':0,'coord_exists':False,'audits':0,'operations':0}


def test_assignment_requires_reason_and_current_eligible_recipient_even_on_replay():
    actor=person();recipient=person();identity=task();key=uid()
    with login(actor) as client:
        mutate(client,identity,'assign',{'version':1,'assignee_id':recipient['id'],'reason':'   '},status=422)
        result=mutate(client,identity,'assign',{'version':1,'assignee_id':recipient['id'],'reason':'Reviewed handoff'},key=key).json()
        assert result['assignee']['id']==recipient['id'] and result['status']=='open'
        with SessionLocal.begin() as db:
            assignment=db.get(CareAssignment,(recipient['id'],'patient-001'));assignment.active=False
        mutate(client,identity,'assign',{'version':1,'assignee_id':recipient['id'],'reason':'Reviewed handoff'},key=key,status=404)
    assert state(identity)['updates']==1 and state(identity)['operations']==1


def test_actor_care_scope_revocation_is_revalidated_before_replay():
    actor=person();identity=task();key=uid()
    with login(actor) as client:
        mutate(client,identity,'claim',{'version':1},key=key)
        with SessionLocal.begin() as db:db.get(CareAssignment,(actor['id'],'patient-001')).active=False
        mutate(client,identity,'claim',{'version':1},key=key,status=404)
    assert state(identity)['updates']==1


def test_persisted_domain_write_revocation_denies_replay_without_restoring_template_grants():
    role='queue-role-'+uid()
    with SessionLocal.begin() as db:
        db.add(Role(id=role,label='Synthetic queue capability'));db.flush()
        db.add_all([RolePermission(role_id=role,permission_id=permission) for permission in ['D06.read','D06.write']])
    actor=person(role=role,care=None);identity=task();key=uid()
    with login(actor) as client:
        mutate(client,identity,'claim',{'version':1},key=key)
        with SessionLocal.begin() as db:db.delete(db.get(RolePermission,(role,'D06.write')))
        mutate(client,identity,'claim',{'version':1},key=key,status=403)
    assert state(identity)['updates']==state(identity)['operations']==1


@pytest.mark.parametrize('body',[{'version':True,'due_at':None,'priority':'normal'},
    {'version':1,'due_at':'2026-11-15T10:00:00','priority':'normal'},
    {'version':1,'due_at':None,'priority':'clinical_emergency'}])
def test_schedule_rejects_nonversion_naive_time_and_untyped_priority(body):
    identity=task()
    with login() as client:mutate(client,identity,'schedule',body,status=422)
    assert not state(identity)['coord_exists']


def test_schedule_can_clear_due_date_and_replay_equivalent_utc_instant():
    identity=task();key=uid();due=utcnow()+timedelta(hours=1)
    with login() as client:
        first=mutate(client,identity,'schedule',{'version':1,'due_at':due.isoformat(),'priority':'low'},key=key).json()
        replay=mutate(client,identity,'schedule',{'version':1,'due_at':due.isoformat().replace('+00:00','Z'),'priority':'low'},key=key).json();assert replay==first
        clear=mutate(client,identity,'schedule',{'version':2,'due_at':None,'priority':'normal'}).json()
        assert clear['due_at'] is None and not clear['overdue']


def test_overdue_escalation_is_bounded_same_obligation_owner_and_idempotent():
    owner=person();identity=task(assignee=owner['id'],coord={'due_at':utcnow()-timedelta(minutes=1)})
    with login(owner) as client:
        for level in range(1,4):
            key=uid();body={'version':level,'reason':'Overdue operational handoff'}
            first=mutate(client,identity,'escalate',body,key=key).json()
            assert first['escalation_level']==level and first['assignee_id']==owner['id'] and first['status']=='open' and first['escalated_at']
            assert mutate(client,identity,'escalate',body,key=key).json()==first
        mutate(client,identity,'escalate',{'version':4,'reason':'No fourth escalation'},status=409)
        assert not read(client,identity)['capabilities']['escalate']
    assert state(identity)=={'version':4,'owner':owner['id'],'status':'open','updates':3,'level':3,'coord_exists':True,'audits':3,'operations':3}


def test_future_or_undated_work_cannot_be_escalated():
    for coord in [None,{'due_at':utcnow()+timedelta(days=1)}]:
        identity=task(coord=coord);before=state(identity)
        with login() as client:mutate(client,identity,'escalate',{'version':1,'reason':'Not overdue'},status=409)
        assert state(identity)==before


@pytest.mark.parametrize('status',['completed','cancelled'])
def test_terminal_tasks_reject_all_coordination_and_replay(status):
    actor=person();recipient=person();identity=task();key=uid()
    with login(actor) as client:
        claimed=mutate(client,identity,'claim',{'version':1},key=key).json()
        with SessionLocal.begin() as db:row=db.get(Task,identity);row.status=status;row.version+=1
        before=state(identity)
        for action,body in [('claim',{'version':1}),('release',{'version':claimed['version']}),
            ('assign',{'version':claimed['version'],'assignee_id':recipient['id'],'reason':'Cannot hand off closed work'}),
            ('schedule',{'version':claimed['version'],'due_at':None,'priority':'normal'}),
            ('escalate',{'version':claimed['version'],'reason':'Closed work'})]:
            mutate(client,identity,action,body,key=key if action=='claim' else None,status=409)
        assert state(identity)==before


def test_csrf_idempotency_conflict_and_missing_key_are_guarded():
    identity=task();key=uid()
    with login() as client:
        csrf=client.headers.pop('X-CSRF-Token');mutate(client,identity,'claim',{'version':1},status=403);client.headers['X-CSRF-Token']=csrf
        assert client.post('/api/v2/team-queue/tasks/'+identity+'/claim',json={'version':1}).status_code==422
        mutate(client,identity,'claim',{'version':1},key=key)
        mutate(client,identity,'schedule',{'version':2,'due_at':None,'priority':'normal'},key=key,status=409)
    assert state(identity)['updates']==1


def test_audit_failure_rolls_back_owner_coordination_version_and_operation(monkeypatch):
    identity=task()
    def fail(*args,**kwargs):raise RuntimeError('Synthetic audit failure')
    monkeypatch.setattr(team_queue,'audit',fail)
    with login(raise_errors=False) as client:
        response=client.post('/api/v2/team-queue/tasks/'+identity+'/claim',json={'version':1},headers={'Idempotency-Key':uid()});assert response.status_code==500
    assert state(identity)=={'version':1,'owner':None,'status':'open','updates':0,'level':0,'coord_exists':False,'audits':0,'operations':0}


def test_order_and_ai_completion_remain_domain_guarded():
    order_task=task(domain='D10');proposal_task=task(domain='D37',status='in_progress')
    with SessionLocal.begin() as db:
        db.add(ClinicalOrder(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',encounter_id='encounter-001',
            task_id=order_task,requester_id='user-clinician',kind='lab',code='QUEUE-SYN',label='Synthetic queue order',status='signed'))
        run=InferenceRun(id=uid(),task_id=proposal_task,actor_id='user-clinician',provider='mock_demo',outcome='success',elapsed_ms=0);db.add(run);db.flush()
        document=db.get(Document,'document-patient-001');encounter=db.get(Encounter,'encounter-001')
        db.add(Proposal(id=uid(),task_id=proposal_task,run_id=run.id,document_version_id=document.current_version_id,
            encounter_version=encounter.version,task_version=1,action_canonical='{}',action_hash='a'*64,expires_at=utcnow()+timedelta(hours=1)))
    with login() as client:
        for identity,code in [(order_task,'ORDER_TASK_REQUIRES_DOMAIN_ACTION'),(proposal_task,'AI_TASK_REQUIRES_REVIEW_COMMIT')]:
            claimed=mutate(client,identity,'claim',{'version':1}).json()
            response=client.post('/api/v2/tasks/'+identity+'/transition',json={'version':claimed['version'],'target':'completed'},headers={'Idempotency-Key':uid()})
            assert response.status_code==409 and response.json()['detail']['code']==code
        with SessionLocal() as db:assert db.scalar(select(ClinicalOrder.status).where(ClinicalOrder.task_id==order_task))=='signed'


def test_team_queue_does_not_generate_or_select_assistant_source_bodies(monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Coordination must never prepare AI')
    monkeypatch.setattr(assistant_provider,'prepare_assistant',forbidden);monkeypatch.setattr(assistant_core,'enqueue',forbidden)
    identity=task();statements=[]
    def capture(conn,cursor,statement,*args):statements.append(statement.lower())
    with login() as client:
        event.listen(engine,'before_cursor_execute',capture)
        try:
            assert client.get('/api/v2/team-queue',params={'q':identity}).status_code==200
            first=mutate(client,identity,'claim',{'version':1}).json()
            mutate(client,identity,'schedule',{'version':first['version'],'due_at':None,'priority':'normal'})
        finally:event.remove(engine,'before_cursor_execute',capture)
    assert statements and not any(word in sql for sql in statements for word in ['source_manifest','inference_view','assistant_revisions','document_versions'])


def test_corrupt_operational_counter_fails_closed_without_writes():
    identity=task(coord={'operational_updates':99});before=state(identity)
    try:
        with login() as client:
            response=mutate(client,identity,'claim',{'version':1},status=409)
            assert response.json()['detail']['code']=='TASK_OPERATIONAL_VERSION_INVALID'
        assert state(identity)==before
    finally:
        # Keep this deliberately corrupt fixture out of later source-packet tests.
        with SessionLocal.begin() as db:db.get(TaskCoordination,identity).operational_updates=0


def _packet_for_client(client):
    from backend.app.auth import actor_for
    from backend.app.assistant_collectors import collect_packet
    with SessionLocal() as db:
        session=db.scalar(select(SessionRecord).where(SessionRecord.token_hash==text_hash(client.cookies.get('his_session'))))
        actor=actor_for(db,db.get(User,session.user_id),session)
        return collect_packet(db,actor,'nursing_handover','patient-001','encounter-001')


def test_real_collector_digest_ignores_coordination_but_tracks_domain_status_change():
    actor=person();identity=task()
    with login(actor) as client:
        before=_packet_for_client(client)['source_digest']
        claimed=mutate(client,identity,'claim',{'version':1}).json()
        assert _packet_for_client(client)['source_digest']==before
        scheduled=mutate(client,identity,'schedule',{'version':claimed['version'],'due_at':(utcnow()-timedelta(hours=1)).isoformat(),'priority':'high'}).json()
        escalated=mutate(client,identity,'escalate',{'version':scheduled['version'],'reason':'Operational deadline'}).json()
        assert _packet_for_client(client)['source_digest']==before
        response=client.post('/api/v2/tasks/'+identity+'/transition',json={'version':escalated['version'],'target':'in_progress'},headers={'Idempotency-Key':uid()})
        assert response.status_code==200
        assert _packet_for_client(client)['source_digest']!=before
    persisted=state(identity);assert persisted['version']-persisted['updates']==2


def test_claim_does_not_expose_pristine_generated_task_as_source():
    from backend.app.auth import actor_for
    from backend.app.models_assistant import AssistantEffect,AssistantRevision,AssistantRun
    actor=person();identity=task(title='Synthetic generated followup')
    with login(actor) as client:
        with SessionLocal.begin() as db:
            session=db.scalar(select(SessionRecord).where(SessionRecord.token_hash==text_hash(client.cookies.get('his_session'))))
            effective=actor_for(db,db.get(User,actor['id']),session)
            run=AssistantRun(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',encounter_id='encounter-001',
                actor_id=actor['id'],session_id=session.id,profile='nursing_handover',locale='th',authorization_hash=authorization_hash(effective),
                operation_key=uid(),request_hash='a'*64,source_digest='b'*64,source_manifest={},inference_view={},input_hash='c'*64,
                execution_state='succeeded',review_state='accepted',provider={})
            db.add(run);db.flush()
            revision=AssistantRevision(id=uid(),run_id=run.id,version=1,content_hash=digest({}),source_digest=run.source_digest,artifact={},origin='model',created_by=actor['id'])
            db.add(revision);db.flush()
            db.add(AssistantEffect(id=uid(),run_id=run.id,revision_id=revision.id,action_id='a1',kind='create_nursing_followup_task',task_id=identity,
                receipt={'created':True,'version':1,'status':'open','title':'Synthetic generated followup'}))
        before=_packet_for_client(client)
        assert identity not in {source['id'] for source in before['manifest']['sources']}
        claimed=mutate(client,identity,'claim',{'version':1}).json()
        after=_packet_for_client(client)
        assert after['source_digest']==before['source_digest'] and identity not in {source['id'] for source in after['manifest']['sources']}
        response=client.post('/api/v2/tasks/'+identity+'/transition',json={'version':claimed['version'],'target':'in_progress'},headers={'Idempotency-Key':uid()});assert response.status_code==200
        assert identity in {source['id'] for source in _packet_for_client(client)['manifest']['sources']}
