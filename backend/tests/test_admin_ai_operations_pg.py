"""Admin metadata projections use real PostgreSQL but no provider or chart read."""
import os
import re
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

assert os.environ.get('HIS_TEST_DATABASE_URL')==os.environ.get('DATABASE_URL') and os.environ.get('HIS_TEST_DATABASE_URL')
from backend.app import models as M
from backend.app.db import SessionLocal,engine
from backend.app.main import app
from backend.app.seed import seed
from backend.app.models_assistant import AssistantRun
from backend.app.common import uid,utcnow,authorization_hash,digest
from backend.tests.test_assistant_pg import actor,context
from backend.app.assistant_core import enqueue


@pytest.fixture(scope='module',autouse=True)
def seeded():
    assert engine.url.database=='his_test'
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])


def client_for(role='system_admin'):
    client=TestClient(app);r=client.post('/api/v2/auth/login',json={'username':role,'password':os.environ['HIS_SEED_PASSWORD']});assert r.status_code==200
    return client


def test_admin_only_scalar_operational_projection_and_no_sensitive_sql(monkeypatch):
    secret='NEVER_RETURN_AUTHORED_PATIENT_OR_SECRET'
    with SessionLocal.begin() as db:
        from backend.app.assistant_collectors import collect_packet
        pid,eid,_=context(db);a=actor(db);packet=collect_packet(db,a,'visit_preparation',pid,eid,'en');rid=uid()
        view={**packet['view'],'coverage':{'eligible_sources':7,'included_sources':{'text':secret},'omitted_sources':False,'secret':secret}}
        started=utcnow()-timedelta(seconds=2)
        run=AssistantRun(id=rid,organization_id=a.organization_id,facility_id=a.facility_id,patient_id=pid,encounter_id=eid,actor_id=a.user_id,session_id=a.session_id,profile='visit_preparation',locale='en',authorization_hash=authorization_hash(a),operation_key=uid(),request_hash='e'*64,source_digest=packet['source_digest'],source_manifest=packet['manifest'],inference_view=view,input_hash=digest(view),execution_state='failed',review_state='unavailable',error=secret,provider={'api_key':secret,'prompt':secret,'model':secret},measured_cost=secret,usage={'prompt_eval_count':secret,'eval_count':True,'prompt_eval_duration':10**1000,'eval_duration':123,'total_duration':{'text':secret},'raw':secret},started_at=started,completed_at=started+timedelta(seconds=1))
        db.add(run)
    import backend.app.admin_ai as admin_ai
    monkeypatch.setattr(admin_ai,'assistant_provider_config',lambda:{'enabled':True,'configured':True,'route':'dr_train_gpu0_v1','profiles_qualified':['visit_preparation']})
    client=client_for();statements=[]
    def capture(conn,cursor,statement,params,context,executemany):statements.append(statement)
    event.listen(engine,'before_cursor_execute',capture)
    try:response=client.get('/api/v2/admin/ai-operations',params={'state':'failed','limit':50})
    finally:event.remove(engine,'before_cursor_execute',capture)
    assert response.status_code==200
    assert secret not in response.text and pid not in response.text and eid not in response.text
    result=response.json();item=next(item for item in result['items'] if item['id']==rid)
    assert item['error']=='OTHER_FAILURE' and item['measured_cost'] is None and item['elapsed_ms']==1000
    assert item['usage']=={'prompt_eval_count':None,'eval_count':None,'prompt_eval_duration':None,'eval_duration':123,'total_duration':None}
    assert item['coverage']=={'eligible_sources':7,'included_sources':None,'omitted_sources':None,'partial_sources':0}
    assert result['worker']['heartbeat_status']=='not_observed' and result['worker']['heartbeat_at'] is None
    assert item['evidence_freshness']=='not_checked_for_admin' and result['provider']['live_status']=='not_checked'
    selected=[sql for sql in statements if sql.lstrip().upper().startswith('SELECT')]
    assert not any(re.search(r'assistant_runs\.source_manifest(?:\s+AS|\s*,|\s+FROM)',sql) or 'assistant_revisions.artifact' in sql or 'document_versions.content' in sql for sql in selected)
    assert not any('assistant_runs.patient_id' in sql or 'assistant_runs.encounter_id' in sql or 'assistant_runs.session_id' in sql or 'assistant_runs.provider' in sql for sql in selected)


def test_admin_scoping_pagination_filter_validation_and_staff_denial():
    client=client_for();first=client.get('/api/v2/admin/ai-operations',params={'limit':1}).json()
    second=client.get('/api/v2/admin/ai-operations',params={'limit':1,'offset':1}).json()
    assert first['scope']=={'organization_id':'org-demo','facility_id':'facility-demo'}
    assert len(first['items'])<=1 and len(second['items'])<=1
    if first['items'] and second['items']:assert first['items'][0]['id']!=second['items'][0]['id']
    assert client.get('/api/v2/admin/ai-operations?limit=51').status_code==422
    assert client.get('/api/v2/admin/ai-operations?state=pretend_success').status_code==422
    assert client_for('clinician').get('/api/v2/admin/ai-operations').status_code==403
    assert client_for('patient').get('/api/v2/admin/ai-operations').status_code==403
    assert TestClient(app).get('/api/v2/admin/ai-operations').status_code==401


def test_admin_other_facility_and_organization_jobs_are_excluded():
    with SessionLocal.begin() as db:
        organization=uid();facility=uid();pid=uid();eid=uid();user=uid()
        db.add(M.Organization(id=organization,name='Other fictional organization'));db.flush()
        db.add(M.Facility(id=facility,organization_id=organization,name='Other fictional facility'));db.flush()
        db.add(M.Patient(id=pid,organization_id=organization,facility_id=facility,display_name='Private other patient'));db.flush()
        db.add(M.Encounter(id=eid,patient_id=pid,organization_id=organization,facility_id=facility));db.flush()
        db.add(M.User(id=user,organization_id=organization,username=uid(),display_name='Other staff',password_hash='not-a-login'));db.flush()
        session=M.SessionRecord(id=uid(),user_id=user,facility_id=facility,token_hash=uid(),csrf_hash=uid(),csrf_token=uid(),expires_at=utcnow()+timedelta(hours=1));db.add(session);db.flush()
        foreign_id=uid();db.add(AssistantRun(id=foreign_id,organization_id=organization,facility_id=facility,patient_id=pid,encounter_id=eid,actor_id=user,session_id=session.id,profile='visit_preparation',locale='en',authorization_hash='a'*64,operation_key=uid(),request_hash='b'*64,source_digest='c'*64,source_manifest={},inference_view={},input_hash='d'*64,execution_state='succeeded',review_state='pending',provider={}))
    response=client_for().get('/api/v2/admin/ai-operations?limit=50')
    assert response.status_code==200 and foreign_id not in response.text and organization not in response.text and pid not in response.text
