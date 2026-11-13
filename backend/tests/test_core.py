import json,os,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,text,func
from sqlalchemy.exc import IntegrityError
from backend.app.main import app
from backend.app.db import SessionLocal
from backend.app.models import *
from backend.app.common import utcnow
PASSWORD=os.environ['HIS_SEED_PASSWORD']
TRACE=[]
def client(username='clinician'):
    c=TestClient(app);r=c.post('/api/v2/auth/login',json={'username':username,'password':PASSWORD});assert r.status_code==200,r.text
    c.headers['X-CSRF-Token']=r.json()['csrf_token'];return c

def mutate(c,path,data,expect=200,key=None,method='post'):
    r=getattr(c,method)('/api/v2'+path,json=data,headers={'Idempotency-Key':key or str(uuid.uuid4())});assert r.status_code==expect,(path,r.status_code,r.text);return r.json()

def test_01_journey_registration_document_ai():
    reg=client('registration');p=mutate(reg,'/patients',{'display_name':'ผู้ป่วย J01 ใหม่','identifier':'J01-'+str(uuid.uuid4()),'sex':'unknown'},201)
    for target in ['verified','active']:p=mutate(reg,f"/patients/{p['id']}/transition",{'version':p['version'],'target':target})
    appointment=mutate(reg,'/clinical/D02/records',{'patient_id':p['id'],'slot_id':'slot-demo','reason':'J01 synthetic appointment'},201)
    for action in ['booked','checked_in','called']:
        appointment=mutate(reg,f"/clinical/D02/records/{appointment['id']}/actions",{'version':appointment['version'],'action':action})
    e=reg.get('/api/v2/encounters/'+appointment['encounter_id']).json()
    clinician=client();assert clinician.get('/api/v2/patients/'+p['id']).status_code==404
    admin=client('system_admin');mutate(admin,'/admin/users/user-clinician/care-assignments',{'patient_id':p['id'],'active':True})
    assert clinician.get('/api/v2/patients/'+p['id']).status_code==200
    e=mutate(clinician,f"/encounters/{e['id']}/transition",{'version':e['version'],'target':'in_consult'})
    d=mutate(clinician,'/documents',{'patient_id':p['id'],'encounter_id':e['id'],'title':'เอกสาร J01','content':'DEMO ต้นฉบับสังเคราะห์'},201)
    t=mutate(clinician,'/tasks',{'patient_id':p['id'],'encounter_id':e['id'],'domain':'D37','kind':'document_review','title':'ทบทวนเอกสาร'},201)
    proposal=mutate(clinician,'/proposals',{'task_id':t['id'],'document_id':d['id']})['proposal']
    old=proposal.copy();proposal=mutate(clinician,f"/proposals/{proposal['id']}/review",{'version':proposal['version'],'action_hash':proposal['action_hash'],'decision':'edit','edited_text':'DEMO ผู้ตรวจแก้ข้อความ'})
    mutate(clinician,f"/proposals/{proposal['id']}/review",{'version':old['version'],'action_hash':old['action_hash'],'decision':'approve'},409)
    proposal=mutate(clinician,f"/proposals/{proposal['id']}/review",{'version':proposal['version'],'action_hash':proposal['action_hash'],'decision':'approve'})
    payload={'version':proposal['version'],'action_hash':proposal['action_hash']};key=str(uuid.uuid4())
    result=mutate(clinician,f"/proposals/{proposal['id']}/commit",payload,key=key)
    replay=mutate(clinician,f"/proposals/{proposal['id']}/commit",payload,key=key);assert replay==result
    read=clinician.get('/api/v2/results',params={'encounter_id':e['id']}).json()['items'];assert read[0]['id']==result['id']
    assert clinician.get('/api/v2/operations/'+key).json()['response']==result
    assert clinician.get('/api/v2/tasks/'+t['id']).json()['status']=='completed'
    TRACE.append({'journey':'J01','actors':['registration','system_admin','clinician'],'patient_id':p['id'],'appointment_id':appointment['id'],'encounter_id':e['id'],'document_id':d['id'],'task_id':t['id'],'proposal_id':proposal['id'],'result_id':result['id'],'operation_key':key,'assertions':['appointment_queue_to_encounter','care_scope','immutable_edit_binding','same_key_replay','persisted_result']})

def test_02_auth_and_scope():
    anonymous=TestClient(app);assert anonymous.get('/api/v2/patients',headers={'Authorization':'Bearer demo-reviewer-token'}).status_code==401
    assert anonymous.get('/api/v1/context',headers={'Authorization':'Bearer demo-reviewer-token'}).status_code==404
    assert anonymous.post('/api/v2/auth/login',json={'username':'clinician','password':'wrong'}).status_code==401
    c=client();assert c.get('/api/v2/patients/patient-other').status_code==404;assert c.get('/api/v2/patients/patient-second').status_code==404
    raw=c.headers.pop('X-CSRF-Token');assert c.post('/api/v2/auth/logout').status_code==403;c.headers['X-CSRF-Token']=raw
    assert c.post('/api/v2/auth/logout').status_code==200;assert c.get('/api/v2/auth/me').status_code==401
    portal=client('patient');assert portal.get('/api/v2/patients').status_code==403
    admin=client('system_admin');assert admin.get('/api/v2/proposals').status_code==403

def test_03_unique_context_and_immutable_history():
    reg=client('registration');payload={'display_name':'duplicate test','identifier':str(uuid.uuid4()),'issuer':'LOCAL'}
    p=mutate(reg,'/patients',payload,201);mutate(reg,'/patients',payload,409)
    c=client();mutate(c,'/documents',{'patient_id':'patient-001','encounter_id':'encounter-002','title':'bad','content':'bad'},404)
    d=mutate(c,'/documents',{'patient_id':'patient-001','encounter_id':'encounter-001','title':'immutable','content':'original'},201)
    first=d['current_version_id'];d=mutate(c,'/documents/'+d['id']+'/transition',{'version':d['version'],'target':'in_review','content_hash':d['content_hash']})
    d=mutate(c,'/documents/'+d['id']+'/transition',{'version':d['version'],'target':'attested','content_hash':d['content_hash']})
    d=mutate(c,'/documents/'+d['id']+'/revise',{'version':d['version'],'content':'amendment','reason':'correct synthetic typo'})
    versions=c.get('/api/v2/documents/'+d['id']+'/versions').json()['items'];assert len(versions)==2 and versions[0]['content']=='original'
    with SessionLocal() as db:
        with pytest.raises(Exception):db.execute(text('update document_versions set content=:v where id=:id'),{'v':'tampered','id':first});db.commit()
        db.rollback()

def test_04_failure_denominators_and_task_boundary():
    c=client()
    for scenario in ['failure','timeout','invalid','abstain']:
        response=mutate(c,'/proposals',{'task_id':'task-patient-002','document_id':'document-patient-002','scenario':scenario});assert response['proposal'] is None and response['run']['measured_cost'] is None
    runs=c.get('/api/v2/runs?task_id=task-patient-002').json()['items'];assert len(runs)>=4
    task=mutate(c,'/tasks',{'patient_id':'patient-001','encounter_id':'encounter-001','domain':'D10','kind':'lab','title':'not AI'},201)
    mutate(c,'/proposals',{'task_id':task['id'],'document_id':'document-patient-001'},422)

def test_05_j07_revocation_scope_switch_and_replay():
    admin=client('system_admin');username='registration_'+uuid.uuid4().hex[:8]
    u=mutate(admin,'/admin/users',{'username':username,'display_name':'scope test','password':PASSWORD,'role':'registration','facility_id':'facility-demo'},201)
    c=client(username);key=str(uuid.uuid4());payload={'display_name':'scope replay','identifier':str(uuid.uuid4())};p=mutate(c,'/patients',payload,201,key)
    grant=mutate(admin,f"/admin/users/{u['id']}/memberships",{'version':u['version'],'role':'registration','facility_id':'facility-second','active':True})
    mutate(c,'/auth/context',{'membership_id':grant['membership']['id']})
    assert c.get('/api/v2/operations/'+key).status_code==404
    mutate(c,'/patients',payload,409,key)
    assert c.get('/api/v2/patients/'+p['id']).status_code==404
    sessions=admin.get('/api/v2/admin/sessions').json()['items'];session=next(s for s in sessions if s['user_id']==u['id'])
    mutate(admin,'/admin/sessions/'+session['id']+'/revoke',{});assert c.get('/api/v2/auth/me').status_code==401
    TRACE.append({'journey':'J07','actors':['system_admin',username],'user_id':u['id'],'session_id':session['id'],'patient_id':p['id'],'assertions':['scope_switch','cross_scope_replay_denied','revoked_session_denied']})

def test_06_concurrent_commit_atomicity():
    c=client();t=mutate(c,'/tasks',{'patient_id':'patient-003','encounter_id':'encounter-003','domain':'D37','kind':'document_review','title':'concurrent'},201)
    p=mutate(c,'/proposals',{'task_id':t['id'],'document_id':'document-patient-003'})['proposal'];p=mutate(c,'/proposals/'+p['id']+'/review',{'version':p['version'],'action_hash':p['action_hash'],'decision':'approve'})
    payload={'version':p['version'],'action_hash':p['action_hash']};key=str(uuid.uuid4());cookie=dict(c.cookies);headers=dict(c.headers)
    def request():
        with TestClient(app) as cc:
            cc.cookies.update(cookie);cc.headers.update(headers);return mutate(cc,'/proposals/'+p['id']+'/commit',payload,key=key)
    with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(lambda _:request(),range(2)))
    assert a['id']==b['id']
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(CommittedResult).where(CommittedResult.proposal_id==p['id']))==1

def test_99_emit_evidence():
    path=Path('evidence/fullsystem/core-journeys.json');path.parent.mkdir(parents=True,exist_ok=True)
    with SessionLocal() as db:pg=db.scalar(text('show server_version'))
    path.write_text(json.dumps({'postgres_version':pg,'scope':'HTTP TestClient + actual PostgreSQL; not browser','journeys':TRACE},ensure_ascii=False,indent=2))


def test_08_order_lifecycle_and_versioned_revision():
    clinician=client();lab=client('laboratory')
    o=mutate(clinician,'/orders',{'patient_id':'patient-001','encounter_id':'encounter-001','kind':'lab','code':'SYN-LAB','label':'Synthetic lab','instructions':'Manual test only'},201)
    o=mutate(clinician,'/orders/'+o['id']+'/transition',{'version':o['version'],'target':'signed'})
    first_task=o['task_id'];assert lab.get('/api/v2/tasks/'+first_task).status_code==200
    o=mutate(clinician,'/orders/'+o['id']+'/revise',{'version':o['version'],'instructions':'Revised manual instruction'})
    assert lab.get('/api/v2/tasks/'+first_task).json()['status']=='cancelled'
    o=mutate(clinician,'/orders/'+o['id']+'/transition',{'version':o['version'],'target':'signed'})
    assert o['task_id']!=first_task
    for target in ['acknowledged','in_progress','completed']:o=mutate(lab,'/orders/'+o['id']+'/transition',{'version':o['version'],'target':target})
    assert lab.get('/api/v2/tasks/'+o['task_id']).json()['status']=='completed'
    assert len(clinician.get('/api/v2/orders/'+o['id']).json()['revisions'])==1

def test_09_stale_task_and_document_and_provider_config(monkeypatch):
    c=client();t=mutate(c,'/tasks',{'patient_id':'patient-004','encounter_id':'encounter-004','domain':'D37','kind':'document_review','title':'stale target'},201)
    p=mutate(c,'/proposals',{'task_id':t['id'],'document_id':'document-patient-004'})['proposal']
    mutate(c,'/tasks/'+t['id']+'/transition',{'version':t['version'],'target':'in_progress'})
    mutate(c,'/proposals/'+p['id']+'/review',{'version':p['version'],'action_hash':p['action_hash'],'decision':'approve'},409)
    monkeypatch.setenv('HIS_AI_PROVIDER','cloud_api')
    r=mutate(c,'/proposals',{'task_id':'task-patient-004','document_id':'document-patient-004'},503)
    assert r['detail']['fallback'] is False

def test_10_seed_does_not_restore_revoked_permissions():
    from backend.app.seed import seed
    with SessionLocal.begin() as db:
        permission=db.get(RolePermission,('registration','D22.write'));db.delete(permission)
    with SessionLocal.begin() as db:seed(db,PASSWORD)
    with SessionLocal() as db:assert db.get(RolePermission,('registration','D22.write')) is None
    admin=client('system_admin');roles=admin.get('/api/v2/admin/roles').json()
    role=next(r for r in roles['items'] if r['role']=='registration')
    assert 'D22.write' not in role['permissions'] and 'D22.write' in role['declared_template_permissions']

def test_11_sensitive_document_content_and_denials_audited():
    reg=client('registration');docs=reg.get('/api/v2/documents?encounter_id=encounter-001').json()['items'];assert docs and all(d['content'] is None for d in docs)
    assert reg.get('/api/v2/documents/document-patient-001/versions').status_code==403
    billing=client('billing');metadata=billing.get('/api/v2/documents/document-patient-001').json()
    mutate(billing,'/documents/document-patient-001/transition',{'version':metadata['version'],'target':'in_review','content_hash':metadata['content_hash']},403)
    admin=client('system_admin');events=admin.get('/api/v2/admin/security-events').json()['items'];assert any(e['status_code']==403 for e in events)
    assert all('password' not in e and 'token' not in e and 'body' not in e for e in events)

def test_12_commit_failure_never_returns_success(monkeypatch):
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    c=client('registration');marker=str(uuid.uuid4());armed=[True]
    def fail_once(db):
        if armed[0]:
            armed[0]=False
            raise IntegrityError('synthetic before-commit fault',{},Exception('injected rollback'))
    event.listen(Session,'before_commit',fail_once)
    try:mutate(c,'/patients',{'display_name':'commit rollback','identifier':marker},409)
    finally:event.remove(Session,'before_commit',fail_once)
    with SessionLocal() as db:assert db.scalar(select(PatientIdentifier).where(PatientIdentifier.value==marker)) is None

def test_13_cached_session_revocation_revalidated():
    from backend.app.auth import actor_for,revalidate_actor
    from fastapi import HTTPException
    admin=client('system_admin');username='revoked_'+uuid.uuid4().hex[:8]
    u=mutate(admin,'/admin/users',{'username':username,'display_name':'revoke race','password':PASSWORD,'role':'registration','facility_id':'facility-demo'},201)
    c=client(username)
    with SessionLocal() as request_db:
        session=request_db.scalar(select(SessionRecord).where(SessionRecord.user_id==u['id']))
        actor=actor_for(request_db,request_db.get(User,u['id']),session)
        with SessionLocal.begin() as other:
            other.get(SessionRecord,session.id).revoked_at=utcnow()
        with pytest.raises(HTTPException) as rejected:revalidate_actor(request_db,actor)
        assert rejected.value.status_code==401
    assert c.get('/api/v2/auth/me').status_code==401

def test_14_different_keys_commit_once():
    c=client();t=mutate(c,'/tasks',{'patient_id':'patient-003','encounter_id':'encounter-003','domain':'D37','kind':'document_review','title':'different keys'},201)
    p=mutate(c,'/proposals',{'task_id':t['id'],'document_id':'document-patient-003'})['proposal'];p=mutate(c,'/proposals/'+p['id']+'/review',{'version':p['version'],'action_hash':p['action_hash'],'decision':'approve'})
    payload={'version':p['version'],'action_hash':p['action_hash']};cookies=dict(c.cookies);headers=dict(c.headers)
    def one(_):
        with TestClient(app) as cc:
            cc.cookies.update(cookies);cc.headers.update(headers)
            return cc.post('/api/v2/proposals/'+p['id']+'/commit',json=payload,headers={'Idempotency-Key':str(uuid.uuid4())}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(one,range(2)))
    assert sorted(statuses)==[200,409]
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(CommittedResult).where(CommittedResult.proposal_id==p['id']))==1

def test_15_expiry_and_foreign_keys():
    c=client('auditor')
    with SessionLocal.begin() as db:
        session=db.scalar(select(SessionRecord).where(SessionRecord.user_id=='user-auditor').order_by(SessionRecord.created_at.desc()));session.expires_at=utcnow()-timedelta(seconds=1)
    assert c.get('/api/v2/auth/me').status_code==401
    with SessionLocal() as db:
        db.add(Encounter(organization_id='org-demo',facility_id='facility-demo',patient_id='patient-other',status='waiting'))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()

def test_16_changed_document_blocks_commit_and_revoked_reviewer():
    c=client();admin=client('system_admin')
    def proposal(document):
        t=mutate(c,'/tasks',{'patient_id':'patient-001','encounter_id':'encounter-001','domain':'D37','kind':'document_review','title':'review guards'},201)
        return mutate(c,'/proposals',{'task_id':t['id'],'document_id':document['id']})['proposal']
    d=mutate(c,'/documents',{'patient_id':'patient-001','encounter_id':'encounter-001','title':'evidence guard','content':'first evidence'},201)
    p=proposal(d);p=mutate(c,'/proposals/'+p['id']+'/review',{'version':p['version'],'action_hash':p['action_hash'],'decision':'approve'})
    d=mutate(c,'/documents/'+d['id']+'/revise',{'version':d['version'],'content':'changed source','reason':'manual update'})
    mutate(c,'/proposals/'+p['id']+'/commit',{'version':p['version'],'action_hash':p['action_hash']},409)
    username='reviewer_'+uuid.uuid4().hex[:8]
    u=mutate(admin,'/admin/users',{'username':username,'display_name':'reviewer recheck','password':PASSWORD,'role':'clinician','facility_id':'facility-demo'},201)
    mutate(admin,'/admin/users/'+u['id']+'/care-assignments',{'patient_id':'patient-001','active':True})
    reviewer=client(username);p=proposal(d);p=mutate(reviewer,'/proposals/'+p['id']+'/review',{'version':p['version'],'action_hash':p['action_hash'],'decision':'approve'})
    mutate(admin,'/admin/users/'+u['id']+'/memberships',{'version':u['version'],'facility_id':'facility-demo','role':'clinician','active':False})
    mutate(c,'/proposals/'+p['id']+'/commit',{'version':p['version'],'action_hash':p['action_hash']},409)
    with SessionLocal() as db:assert db.scalar(select(CommittedResult).where(CommittedResult.proposal_id==p['id'])) is None

def test_17_finance_reference_is_metadata_not_clinical_access():
    c=client('finance');patients=c.get('/api/v2/reference/patients');encounters=c.get('/api/v2/reference/encounters?patient_id=patient-001')
    assert patients.status_code==200 and encounters.status_code==200
    assert all(set(p)=={'id','display_name','status'} for p in patients.json()['items'])
    assert all(set(e)=={'id','patient_id','kind','status','version'} for e in encounters.json()['items'])
    assert c.get('/api/v2/patients').status_code==403 and c.get('/api/v2/encounters').status_code==403
    assert c.get('/api/v2/reference/encounters?patient_id=patient-other').status_code==404

def test_18_tool_boundary_and_role_home_records():
    from dataclasses import replace
    from fastapi import HTTPException
    from backend.app.auth import actor_for,revalidate_actor
    c=client('finance');home=c.get('/api/v2/home').json()
    assert 'domain_counts' in home and all(x['domain'] in ('D23','D24','D25','D26') for x in home['domain_counts'])
    assert all(x['record_count']>=x['pending_count'] and x['href'].startswith('/domains/') for x in home['domain_counts'])
    clinical=client();home=clinical.get('/api/v2/home').json();assert next(x for x in home['domain_counts'] if x['domain']=='D01')['record_count']>=4
    with SessionLocal() as db:
        session=db.scalar(select(SessionRecord).where(SessionRecord.user_id=='user-clinician').order_by(SessionRecord.created_at.desc()))
        actor=actor_for(db,db.get(User,'user-clinician'),session)
        forged=replace(actor,user_id='user-system_admin')
        with pytest.raises(HTTPException) as rejected:revalidate_actor(db,forged)
        assert rejected.value.status_code==401
