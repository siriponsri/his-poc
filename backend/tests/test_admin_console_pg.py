"""Administration scope/policy on an explicitly disposable PostgreSQL18 database.

No live provider, server, account provisioning or shared service is used.
"""
import io
import json
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event,func,select,text
from sqlalchemy.exc import SQLAlchemyError

assert os.getenv('HIS_TEST_DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL'),'Disposable PostgreSQL wrapper required'

from backend.app import admin,assistant_provider
from backend.app.auth import permissions_for
from backend.app.common import uid,utcnow
from backend.app.db import SessionLocal,engine
from backend.app.main import app
from backend.app.models import Membership,Role,RolePermission,SecurityEvent,SessionRecord,User
from backend.app.models_assistant import AssistantRun,AssistantWatch
from backend.app.provision_poc_admin import ProvisionError,provision_poc_admin,main as provision_main
from backend.app.seed import seed


@pytest.fixture(scope='module',autouse=True)
def synthetic_admin():
    assert engine.url.database=='his_test' and engine.url.host=='127.0.0.1'
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])
    # The requested private owner's password is never available to tests.
    password=secrets.token_urlsafe(12)[:9]
    def invoke(_):
        with SessionLocal.begin() as db:
            return provision_poc_admin(db,username='admin',organization_id='org-demo',facility_id='facility-demo',password=password)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(invoke,range(2)))
    assert sorted(row['status'] for row in results)==['CREATED','UNCHANGED']
    assert len({row['user_id'] for row in results})==1
    return {'password':password,'id':results[0]['user_id']}


def login(username='system_admin',password=None):
    client=TestClient(app)
    response=client.post('/api/v2/auth/login',json={'username':username,'password':password or os.environ['HIS_SEED_PASSWORD']})
    assert response.status_code==200
    client.headers['X-CSRF-Token']=response.json()['csrf_token']
    return client


def add_user(db,*,organization='org-demo',facility='facility-demo',role='registration',status='active',username=None,display_name='Admin test person'):
    identity=uid()
    hashed=db.get(User,'user-system_admin').password_hash
    user=User(id=identity,organization_id=organization,username=username or 'admin-test-'+identity,display_name=display_name,password_hash=hashed,status=status)
    db.add(user);db.flush()
    db.add(Membership(id=uid(),user_id=identity,facility_id=facility,role=role,active=True));db.flush()
    return user


def read_overview(client):
    response=client.get('/api/v2/admin/overview');assert response.status_code==200
    return response.json()


def test_anonymous_and_normal_roles_cannot_read_administration_metadata():
    with TestClient(app) as client:
        assert client.get('/api/v2/admin/overview').status_code==401
        assert client.get('/api/v2/admin/users').status_code==401
    for role in ('clinician','nurse','registration','laboratory','auditor','patient'):
        with login(role) as client:
            assert client.get('/api/v2/admin/overview').status_code==403
            assert client.get('/api/v2/admin/users').status_code==403


def test_overview_requires_both_persisted_permissions():
    with SessionLocal.begin() as db:
        db.add(Role(id='admin-test-identity-only',label='Test identity only'));db.flush()
        db.add(RolePermission(role_id='admin-test-identity-only',permission_id='identity.admin'))
        user=add_user(db,role='admin-test-identity-only');username=user.username
    with login(username) as client:
        assert client.get('/api/v2/admin/overview').status_code==403


def test_overview_scopes_users_orgwide_and_sessions_exclusively():
    with login() as client:
        before=read_overview(client)
        with SessionLocal.begin() as db:
            user=add_user(db)
            add_user(db,status='suspended');add_user(db,status='disabled')
            add_user(db,organization='org-other',facility='facility-other',status='disabled')
            now=utcnow()
            for facility,expires,revoked in (
                ('facility-second',now+timedelta(hours=1),None),
                ('facility-demo',now-timedelta(hours=1),None),
                ('facility-demo',now-timedelta(hours=1),now-timedelta(hours=2)),
            ):
                db.add(SessionRecord(id=uid(),user_id=user.id,facility_id=facility,token_hash=uid(),csrf_hash=uid(),csrf_token='NEVER_RETURN_SESSION_SECRET',expires_at=expires,revoked_at=revoked))
            foreign=db.get(User,'user-other')
            db.add(SessionRecord(id=uid(),user_id=foreign.id,facility_id='facility-other',token_hash=uid(),csrf_hash=uid(),csrf_token='FOREIGN_SESSION_SECRET',expires_at=now+timedelta(hours=1)))
        after=read_overview(client)
        assert after['scope']=={'organization_id':'org-demo','facility_id':'facility-demo'}
        assert {key:after['users'][key]-before['users'][key] for key in before['users']}=={'total':3,'active':1,'suspended':1,'disabled':1}
        assert {key:after['sessions'][key]-before['sessions'][key] for key in before['sessions']}=={'active':1,'revoked':1,'expired':1}
        assert 'NEVER_RETURN_SESSION_SECRET' not in json.dumps(after)
        assert 'FOREIGN_SESSION_SECRET' not in json.dumps(after)


def test_security_window_filters_facility_event_type_and_time(monkeypatch):
    now=utcnow();monkeypatch.setattr(admin,'utcnow',lambda:now)
    with login() as client:
        before=read_overview(client)['security']['recent_denial_count']
        with SessionLocal.begin() as db:
            for org,facility,created,code,kind in (
                ('org-demo','facility-demo',now,403,'request_denied_or_rejected'),
                ('org-demo','facility-demo',now-timedelta(hours=24),409,'request_denied_or_rejected'),
                ('org-demo','facility-demo',now-timedelta(hours=24,seconds=1),403,'request_denied_or_rejected'),
                ('org-demo','facility-demo',now+timedelta(seconds=1),403,'request_denied_or_rejected'),
                ('org-demo','facility-second',now,403,'request_denied_or_rejected'),
                ('org-other','facility-other',now,403,'request_denied_or_rejected'),
                ('org-demo','facility-demo',now,201,'poc_admin_provisioned'),
            ):
                db.add(SecurityEvent(id=uid(),organization_id=org,facility_id=facility,actor_id=None,created_at=created,method='GET',route_template='/private/NEVER_RETURN_ROUTE',status_code=code,event=kind))
        result=read_overview(client)
        assert result['security']=={'recent_denial_count':before+2,'window_hours':24}
        assert 'NEVER_RETURN_ROUTE' not in json.dumps(result)


def test_assistant_counts_are_facility_metadata_without_generation_or_source_reads(monkeypatch):
    monkeypatch.setattr(assistant_provider,'assistant_provider_config',lambda:{'configured':True,'route':'dr_train_gpu0_v1','engine_version':'0.12.6','profiles_qualified':['records_readiness'],'base_url':'SECRET_INTERNAL_ENDPOINT','token':'SECRET_PROVIDER_TOKEN'})
    monkeypatch.setattr(assistant_provider,'prepare_assistant',lambda *args,**kwargs:pytest.fail('GET overview must not generate'))
    with login() as client:
        before=read_overview(client)['assistant']['counts']
        with SessionLocal.begin() as db:
            session=SessionRecord(id=uid(),user_id='user-clinician',facility_id='facility-demo',token_hash=uid(),csrf_hash=uid(),csrf_token='SECRET_CSRF',expires_at=utcnow()+timedelta(hours=1));db.add(session);db.flush()
            def run(state,review='unavailable',org='org-demo',facility='facility-demo',patient='patient-001',encounter='encounter-001'):
                db.add(AssistantRun(id=uid(),organization_id=org,facility_id=facility,patient_id=patient,encounter_id=encounter,actor_id='user-clinician',session_id=session.id,profile='visit_preparation',locale='th',authorization_hash='a'*64,operation_key=uid(),request_hash='b'*64,source_digest='c'*64,input_hash='d'*64,source_manifest={'SECRET_PATIENT_NOTE':'DO_NOT_READ_CHART'},inference_view={'SECRET_RESULT':'DO_NOT_READ_RESULT'},provider={'endpoint':'SECRET_INTERNAL_ENDPOINT'},execution_state=state,review_state=review))
            for state in ('queued','waiting_for_capacity','running','failed','timeout','invalid_output','abstained','interrupted','stale_context'):run(state)
            run('succeeded','pending');run('succeeded','accepted')
            run('queued',facility='facility-second',patient='patient-second',encounter='encounter-second')
            run('succeeded','pending',org='org-other',facility='facility-other',patient='patient-other',encounter='encounter-other')
            for status,expires in (('active',utcnow()+timedelta(minutes=20)),('active',utcnow()-timedelta(minutes=1)),('paused',utcnow()+timedelta(minutes=20))):
                db.add(AssistantWatch(id=uid(),actor_id='user-clinician',session_id=session.id,organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',encounter_id='encounter-001',profile='visit_preparation',locale='th',authorization_hash='a'*64,status=status,expires_at=expires,next_scan_at=utcnow()))
        statements=[]
        def capture(conn,cursor,statement,*args):statements.append(statement.lower())
        event.listen(engine,'before_cursor_execute',capture)
        try:result=read_overview(client)
        finally:event.remove(engine,'before_cursor_execute',capture)
        assert {key:result['assistant']['counts'][key]-before[key] for key in before}=={'queued':2,'running':1,'succeeded':2,'failed':5,'awaiting_review':1,'active_watches':1}
        assert result['assistant']['live_status']=='not_checked'
        assert result['assistant']['configured'] is True and result['assistant']['profiles_qualified']==['records_readiness']
        assert result['database']=={'reachable':True,'migration':'0006_team_coordination'}
        encoded=json.dumps(result)
        assert all(secret not in encoded for secret in ('SECRET_','DO_NOT_READ','password_hash','csrf','token','patient_id','source_manifest'))
        assistant_selects=[statement for statement in statements if 'from assistant_runs' in statement or 'from assistant_watches' in statement]
        assert assistant_selects and all('count(' in statement for statement in assistant_selects)
        assert all('source_manifest' not in statement and 'inference_view' not in statement and '.provider' not in statement for statement in assistant_selects)


def test_other_organization_admin_sees_only_its_scope():
    with SessionLocal.begin() as db:user=add_user(db,organization='org-other',facility='facility-other',role='system_admin');username=user.username
    with login(username) as client:
        overview=read_overview(client)
        assert overview['scope']=={'organization_id':'org-other','facility_id':'facility-other'}
        listed=client.get('/api/v2/admin/users').json()
        assert listed['items'] and all(row['organization_id']=='org-other' for row in listed['items'])
        assert all(m['facility_id']=='facility-other' for row in listed['items'] for m in row['memberships'])
        assert 'system_admin' not in {row['username'] for row in listed['items']}


def test_user_search_paging_and_persisted_memberships_are_bounded():
    prefix='needle-'+uid()
    with SessionLocal.begin() as db:
        first=add_user(db,username=prefix+'-a',display_name='Literal %_ Needle')
        second=add_user(db,username=prefix+'-b',status='suspended')
        db.add(Membership(id=uid(),user_id=first.id,facility_id='facility-second',role='nurse',active=False))
        # Inconsistent legacy cross-org membership must not be projected.
        db.add(Membership(id=uid(),user_id=first.id,facility_id='facility-other',role='registration',active=True))
        first_id,second_id=first.id,second.id
    with login() as client:
        statements=[]
        def capture(conn,cursor,statement,*args):statements.append(statement.lower())
        event.listen(engine,'before_cursor_execute',capture)
        try:result=client.get('/api/v2/admin/users',params={'q':prefix,'limit':1}).json()
        finally:event.remove(engine,'before_cursor_execute',capture)
        assert (result['total'],result['limit'],result['offset'])==(2,1,0)
        assert [row['id'] for row in result['items']]==[first_id]
        assert all(set(row)=={'id','role','facility_id','active'} for row in result['items'][0]['memberships'])
        assert {row['facility_id'] for row in result['items'][0]['memberships']}=={'facility-demo','facility-second'}
        assert any(row['active'] is False and row['role']=='nurse' for row in result['items'][0]['memberships'])
        projection=[statement for statement in statements if 'from memberships join facilities' in statement]
        assert len(projection)==1 and 'membership' in projection[0]
        next_page=client.get('/api/v2/admin/users',params={'q':prefix,'limit':1,'offset':1}).json()
        assert next_page['total']==2 and [row['id'] for row in next_page['items']]==[second_id]
        filtered=client.get('/api/v2/admin/users',params={'q':prefix,'status':'suspended'}).json()
        assert filtered['total']==1 and [row['id'] for row in filtered['items']]==[second_id]
        literal=client.get('/api/v2/admin/users',params={'q':'%_ Needle'}).json()
        assert literal['total']==1 and literal['items'][0]['id']==first_id
        assert client.get('/api/v2/admin/users',params={'q':"' OR 1=1 --"}).json()['total']==0
        assert all(key not in json.dumps(result) for key in ('password_hash','csrf_token','token_hash'))


def test_exact_user_detail_is_not_a_filtered_page_and_denies_cross_org():
    with SessionLocal.begin() as db:
        user=add_user(db,username='zz-exact-'+uid(),display_name='Exact scoped identity')
        user.version=7;identity=user.id
        db.add(Membership(id=uid(),user_id=identity,facility_id='facility-second',role='nurse',active=False))
    with login() as client:
        assert identity not in {row['id'] for row in client.get('/api/v2/admin/users',params={'limit':1,'q':'no matching name'}).json()['items']}
        response=client.get('/api/v2/admin/users/'+identity)
        assert response.status_code==200
        value=response.json()
        assert value['id']==identity and value['version']==7 and value['username'].startswith('zz-exact-')
        assert {(m['facility_id'],m['role'],m['active']) for m in value['memberships']}=={('facility-demo','registration',True),('facility-second','nurse',False)}
        assert all(set(m)=={'id','role','facility_id','active'} for m in value['memberships'])
        assert all(key not in response.text for key in ('password_hash','csrf','token_hash'))
        for hidden in ('user-other',uid()):
            response=client.get('/api/v2/admin/users/'+hidden)
            assert response.status_code==404 and 'other_registration' not in response.text
    with login('clinician') as client:assert client.get('/api/v2/admin/users/'+identity).status_code==403


def test_sessions_include_scoped_user_identity_without_secret_or_paging_dependency():
    with SessionLocal.begin() as db:
        user=add_user(db,display_name='Session owner shown by server');identity,username=user.id,user.username
        session_id=uid()
        db.add(SessionRecord(id=session_id,user_id=identity,facility_id='facility-demo',token_hash=uid(),csrf_hash=uid(),csrf_token='NEVER_PROJECT_CSRF_VALUE',expires_at=utcnow()+timedelta(hours=1)))
        foreign_id=uid()
        db.add(SessionRecord(id=foreign_id,user_id='user-other',facility_id='facility-other',token_hash=uid(),csrf_hash=uid(),csrf_token='NEVER_PROJECT_FOREIGN_VALUE',expires_at=utcnow()+timedelta(hours=1)))
    with login() as client:
        assert client.get('/api/v2/admin/users',params={'q':'intentionally unmatched directory filter'}).json()['items']==[]
        statements=[]
        def capture(conn,cursor,statement,*args):statements.append(statement.lower())
        event.listen(engine,'before_cursor_execute',capture)
        try:response=client.get('/api/v2/admin/sessions')
        finally:event.remove(engine,'before_cursor_execute',capture)
        assert response.status_code==200
        rows={row['id']:row for row in response.json()['items']}
        assert rows[session_id]['user']=={'id':identity,'username':username,'display_name':'Session owner shown by server'}
        assert rows[session_id]['user_id']==identity and foreign_id not in rows
        assert all(set(row['user'])=={'id','username','display_name'} for row in rows.values())
        assert all(key not in response.text for key in ('password_hash','token_hash','csrf_hash','csrf_token','NEVER_PROJECT','other_registration'))
        directory=[statement for statement in statements if statement.startswith('select users.id, users.username, users.display_name')]
        assert len(directory)==1


@pytest.mark.parametrize('params',[{'limit':0},{'limit':201},{'offset':-1},{'status':'created'},{'q':'x'*121}])
def test_user_query_bounds_reject_invalid_values(params):
    with login() as client:assert client.get('/api/v2/admin/users',params=params).status_code==422


def test_self_last_admin_membership_deactivation_is_rejected_atomically():
    with login() as client:
        with SessionLocal() as db:
            before=db.get(User,'user-system_admin').version
            member=db.scalar(select(Membership).where(Membership.user_id=='user-system_admin',Membership.role=='system_admin',Membership.facility_id=='facility-demo'));identity=member.id
        response=client.post('/api/v2/admin/users/user-system_admin/memberships',json={'version':before,'role':'system_admin','facility_id':'facility-demo','active':False},headers={'Idempotency-Key':uid()})
        assert response.status_code==409 and response.json()['detail']['code']=='SELF_LAST_ADMIN_MEMBERSHIP_REQUIRED'
        with SessionLocal() as db:assert db.get(User,'user-system_admin').version==before and db.get(Membership,identity).active is True
        assert client.get('/api/v2/admin/overview').status_code==200


def test_self_guard_uses_persisted_capability_and_allows_redundant_non_last_deactivation():
    with SessionLocal.begin() as db:
        user=add_user(db,role='system_admin');identity,username=user.id,user.username
        # Existing role now holds an additional persisted capability, rather than
        # relying on the role's label. Revert the test-only grant afterwards.
        db.add(RolePermission(role_id='registration',permission_id='identity.admin'))
        db.add(Membership(id=uid(),user_id=identity,facility_id='facility-demo',role='registration',active=True))
    try:
        with login(username) as client:
            response=client.post('/api/v2/admin/users/'+identity+'/memberships',json={'version':1,'role':'system_admin','facility_id':'facility-demo','active':False},headers={'Idempotency-Key':uid()})
            assert response.status_code==200
            assert response.json()['membership']['active'] is False
            # The surviving identity capability cannot be removed by that actor.
            response=client.post('/api/v2/admin/users/'+identity+'/memberships',json={'version':2,'role':'registration','facility_id':'facility-demo','active':False},headers={'Idempotency-Key':uid()})
            assert response.status_code==409
    finally:
        with SessionLocal.begin() as db:db.delete(db.get(RolePermission,('registration','identity.admin')))


def test_concurrent_self_deactivations_leave_one_capable_membership():
    with SessionLocal.begin() as db:
        user=add_user(db,role='system_admin');identity,username=user.id,user.username
        db.add(RolePermission(role_id='medical_records',permission_id='identity.admin'))
        db.add(Membership(id=uid(),user_id=identity,facility_id='facility-demo',role='medical_records',active=True))
    try:
        with login(username) as client:
            cookies=dict(client.cookies);headers=dict(client.headers)
            def deactivate(role):
                with TestClient(app) as request:
                    request.cookies.update(cookies);request.headers.update(headers)
                    return request.post('/api/v2/admin/users/'+identity+'/memberships',json={'version':1,'role':role,'facility_id':'facility-demo','active':False},headers={'Idempotency-Key':uid()}).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(deactivate,('system_admin','medical_records')))
            assert sorted(codes)==[200,409]
        with SessionLocal() as db:
            active=db.scalars(select(Membership).where(Membership.user_id==identity,Membership.active.is_(True))).all()
            assert len(active)==1 and active[0].role in ('system_admin','medical_records')
            assert db.get(User,identity).version==2
    finally:
        with SessionLocal.begin() as db:db.delete(db.get(RolePermission,('medical_records','identity.admin')))


def test_provision_is_idempotent_without_rehash_reset_or_fake_actor(synthetic_admin):
    identity=synthetic_admin['id']
    with SessionLocal.begin() as db:
        user=db.get(User,identity);before=(user.password_hash,user.version,user.status)
        count=db.scalar(select(func.count()).select_from(SecurityEvent).where(SecurityEvent.event=='poc_admin_provisioned'))
        result=provision_poc_admin(db,username='admin',organization_id='org-demo',facility_id='facility-demo',password=synthetic_admin['password'])
        assert result['status']=='UNCHANGED'
        assert (user.password_hash,user.version,user.status)==before
        assert db.scalar(select(func.count()).select_from(SecurityEvent).where(SecurityEvent.event=='poc_admin_provisioned'))==count
        membership=db.scalars(select(Membership).where(Membership.user_id==identity)).all()
        assert len(membership)==1 and membership[0].role=='system_admin'
        audit=db.scalar(select(SecurityEvent).where(SecurityEvent.route_template=='/operator/provision-poc-admin/users/'+identity))
        assert audit and audit.actor_id is None and audit.method=='CLI' and audit.status_code==201


@pytest.mark.parametrize('change,expected',[
    ('wrong_password','EXISTING_PASSWORD_CONFLICT'),('inactive_user','EXISTING_IDENTITY_CONFLICT'),
    ('foreign_identity','EXISTING_IDENTITY_CONFLICT'),('extra_membership','EXISTING_MEMBERSHIP_CONFLICT'),
    ('inactive_membership','EXISTING_MEMBERSHIP_CONFLICT'),('platform_identity','EXISTING_IDENTITY_CONFLICT'),
    ('role_drift','SYSTEM_ADMIN_PERMISSION_DRIFT'),('wrong_migration','SUPPORTED_SCHEMA_REQUIRED'),
])
def test_provision_conflicts_never_repair_existing_identity(synthetic_admin,monkeypatch,change,expected):
    with SessionLocal() as db:
        tx=db.begin()
        try:
            user=db.get(User,synthetic_admin['id']);password=synthetic_admin['password']
            original=(user.password_hash,user.version)
            if change=='wrong_password':password=secrets.token_urlsafe(12)
            elif change=='inactive_user':user.status='disabled'
            elif change=='foreign_identity':user.organization_id='org-other'
            elif change=='extra_membership':db.add(Membership(id=uid(),user_id=user.id,facility_id='facility-second',role='registration',active=True))
            elif change=='inactive_membership':db.scalar(select(Membership).where(Membership.user_id==user.id)).active=False
            elif change=='platform_identity':monkeypatch.setenv('HIS_PLATFORM_OPERATORS',user.id)
            elif change=='role_drift':db.delete(db.get(RolePermission,('system_admin','identity.admin')))
            elif change=='wrong_migration':db.execute(text("UPDATE alembic_version SET version_num='0004_dr_screening_bridge'"))
            db.flush()
            with pytest.raises(ProvisionError,match=expected):
                provision_poc_admin(db,username='admin',organization_id='org-demo',facility_id='facility-demo',password=password)
            assert (user.password_hash,user.version)==original
        finally:tx.rollback()


@pytest.mark.parametrize('length',[0,7,201])
def test_private_password_policy_bounds(length):
    with SessionLocal.begin() as db:
        with pytest.raises(ProvisionError,match='POC_PRIVATE_PASSWORD_POLICY'):
            provision_poc_admin(db,username='admin',organization_id='org-demo',facility_id='facility-demo',password='p'*length)


@pytest.mark.parametrize('kwargs',[{'username':'another-admin'},{'organization_id':'org-other'},{'facility_id':'facility-other'}])
def test_provision_exception_is_named_poc_only(synthetic_admin,kwargs):
    payload={'username':'admin','organization_id':'org-demo','facility_id':'facility-demo','password':synthetic_admin['password'],**kwargs}
    with SessionLocal.begin() as db:
        with pytest.raises(ProvisionError,match='NAMED_SYNTHETIC_POC_ONLY'):provision_poc_admin(db,**payload)


def test_provisioned_admin_uses_short_private_password_but_has_no_clinical_or_platform_grants(synthetic_admin):
    with login('admin',synthetic_admin['password']) as client:
        actor=client.get('/api/v2/auth/me').json()['user']
        assert actor['roles']==['system_admin']
        assert set(actor['permissions'])==permissions_for({'system_admin'})
        assert not {'clinical.approve','clinical.attest','orders.sign'} & set(actor['permissions'])
        assert read_overview(client)['database']['migration']=='0006_team_coordination'
        assert client.get('/api/v2/documents').status_code==403
        for profile in ('visit_preparation','nursing_handover','records_readiness','laboratory_handoff'):
            assert client.get('/api/v2/assistant/worklist',params={'profile':profile}).status_code==403
        assert client.get('/api/v2/operations/health').json()['can_run_global_operations'] is False
        body={'username':'policy-test-'+uid(),'display_name':'Policy test','password':synthetic_admin['password'],'role':'registration','facility_id':'facility-demo'}
        assert client.post('/api/v2/admin/users',json=body,headers={'Idempotency-Key':uid()}).status_code==422
        assert client.post('/api/v2/admin/users/'+actor['id']+'/reset-password',json={'version':1,'password':synthetic_admin['password']},headers={'Idempotency-Key':uid()}).status_code==422


def test_cli_reads_only_stdin_and_never_prints_password(synthetic_admin,capsys):
    with patch('sys.argv',['provision_poc_admin','--username','admin','--organization','org-demo','--facility','facility-demo','--password-stdin']),patch('sys.stdin',io.StringIO(synthetic_admin['password']+'\n')):
        assert provision_main()==0
    captured=capsys.readouterr()
    assert synthetic_admin['password'] not in captured.out+captured.err
    result=json.loads(captured.out)
    assert result['status']=='UNCHANGED' and 'password_hash' not in result


def test_cli_database_errors_never_print_driver_or_connection_secrets(synthetic_admin,capsys,monkeypatch):
    def fail():raise SQLAlchemyError('driver included SECRET_DATABASE_URL and SECRET_PASSWORD_HASH')
    monkeypatch.setattr(SessionLocal,'begin',fail)
    with patch('sys.argv',['provision_poc_admin','--username','admin','--organization','org-demo','--facility','facility-demo','--password-stdin']),patch('sys.stdin',io.StringIO(synthetic_admin['password']+'\n')):
        assert provision_main()==2
    captured=capsys.readouterr()
    assert captured.out=='' and json.loads(captured.err)=={'status':'NOT_PROVISIONED','code':'DATABASE_OPERATION_FAILED'}
    assert 'SECRET_' not in captured.err and synthetic_admin['password'] not in captured.err
