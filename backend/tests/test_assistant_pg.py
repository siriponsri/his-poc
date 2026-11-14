"""Synthetic, provider-double acceptance on a disposable PostgreSQL 18 database.

No live model, server database, image inference, or Cloudflare credential is used.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, date
from threading import Event
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text, event

assert os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL'), 'Disposable PostgreSQL wrapper required'
from backend.app import models as M
from backend.app.db import SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed
from backend.app.auth import actor_for
from backend.app.common import uid, utcnow, text_hash, digest, canonical
from backend.app.models_assistant import AssistantRun, AssistantRevision, AssistantDecision, AssistantEffect, AssistantWatch
from backend.app.models_clinical import LabRequest, Handover
from backend.app.assistant_profiles import PROFILES
from backend.app.assistant_collectors import collect_packet
from backend.app.assistant_core import enqueue, create_watch, run_dto
from backend.app.assistant_worker import run_once, scan_watches_once
from backend.app.assistant_admission import admission_busy
from backend.app.assistant_effects import apply_run
from backend.app.assistant_api import ApplyInput

CONFIG={'enabled':True,'configured':True,'qualified':True,'profiles_qualified':list(PROFILES),'route':'offline_test_double','timeout_seconds':2}

@pytest.fixture(scope='module',autouse=True)
def seeded():
    assert engine.url.database=='his_test'
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])

def actor(db,role='clinician'):
    session=M.SessionRecord(id=uid(),user_id='user-'+role,facility_id='facility-demo',token_hash=uid(),csrf_hash=uid(),csrf_token=uid(),expires_at=utcnow()+timedelta(hours=1))
    db.add(session);db.flush()
    return actor_for(db,db.get(M.User,'user-'+role),session)

def context(db,lab=True):
    pid='assistant-p-'+uuid.uuid4().hex[:12];eid='assistant-e-'+uuid.uuid4().hex[:12]
    common={'organization_id':'org-demo','facility_id':'facility-demo'}
    db.add(M.Patient(id=pid,**common,display_name='กมลชนก ศรีสาธิต',birth_date=date(1968,2,13),sex='female',status='active'));db.flush()
    db.add(M.Encounter(id=eid,patient_id=pid,**common,status='in_consult'));db.flush()
    for role in ('clinician','nurse'):db.add(M.CareAssignment(user_id='user-'+role,patient_id=pid))
    did=uid();vid=uid()
    db.add(M.Document(id=did,patient_id=pid,encounter_id=eid,**common,title='Clinical source',version=1));db.flush()
    body='Synthetic history: follow-up visit. No diagnosis generated.'
    db.add(M.DocumentVersion(id=vid,document_id=did,version=1,content=body,content_hash=text_hash(body),created_by='user-clinician'));db.flush();db.get(M.Document,did).current_version_id=vid
    if lab:
        task=M.Task(id=uid(),patient_id=pid,encounter_id=eid,**common,domain='D07',kind='lab',title='Synthetic laboratory order');db.add(task);db.flush()
        order=M.ClinicalOrder(id=uid(),patient_id=pid,encounter_id=eid,**common,task_id=task.id,requester_id='user-clinician',kind='lab',code='FPG',label='Fasting plasma glucose',status='signed');db.add(order);db.flush()
        db.add(LabRequest(id=uid(),patient_id=pid,encounter_id=eid,**common,created_by='user-laboratory',status='released',order_id=order.id,order_version=1,analyte='Fasting plasma glucose',specimen_type='plasma',result_value='152',unit='mg/dL',reference_range='70-99',critical=False))
    db.flush()
    return pid,eid,did

def fixture_run(profile='visit_preparation',role='clinician'):
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);a=actor(db,role)
        run,_=enqueue(db,a,profile,pid,eid,'en',uid())
        return a,run.id,pid,eid,did

def artifact(view):
    drafts=[]
    for candidate in view['effect_candidates']:
        if candidate.get('draft_id'):
            drafts.append({'id':candidate['draft_id'],'title':'Prepared draft','text':'Synthetic history for professional review.','source_refs':candidate['source_refs']})
    return {'facts':[{'source_ref':'s1','field':'display_name','display':view['sources'][0]['fields']['display_name']}],'work_gaps':[],'drafts':drafts,'suggested_effects':view['effect_candidates'],'requires_review':True}

def provider(profile,locale,view):
    return {'outcome':'success','reason':None,'artifact':artifact(view),'provenance':{'test_double':True},'usage':{'input_tokens':12,'output_tokens':8},'measured_cost':None,'elapsed_ms':1}

def dispatch(prepare=provider,validate=lambda p,a,v:a,config=CONFIG):
    return run_once(prepare=prepare,validate=validate,config=lambda:config)

def apply_body(db,a,run_id,edited=None,actions=None):
    dto=run_dto(db,a,db.get(AssistantRun,run_id));r=dto['revision']
    return ApplyInput(expected_revision_id=r['id'],expected_version=r['version'],expected_content_hash=r['content_hash'],expected_source_digest=dto['source_digest'],selected_action_ids=actions if actions is not None else [e['action_id'] for e in r['suggested_effects']],edited_draft_text=edited)

@pytest.mark.parametrize('role,profile,has_note,has_lab',[
    ('clinician','visit_preparation',True,True),('nurse','nursing_handover',True,False),('registration','records_readiness',False,False),('laboratory','laboratory_handoff',False,True)])
def test_four_profile_packets_are_role_safe(role,profile,has_note,has_lab):
    with SessionLocal.begin() as db:
        pid,eid,_=context(db);a=actor(db,role)
        packet=collect_packet(db,a,profile,pid,eid,'en')
        rows=packet['manifest']['sources'];view=packet['view']
        assert any('text' in row for row in rows)==has_note
        assert any(row['kind']=='lab' for row in rows)==has_lab
        assert packet['view']['coverage']['eligible_sources']==len(rows)
        assert len(canonical(view).encode('utf-8'))<=2000
        assert len(str(view))<3500
        if role=='registration':
            assert 'Synthetic history' not in str(packet) and 'created_by' not in str(packet)
            assert all('draft_id' not in candidate for candidate in view['effect_candidates'])
        if role=='nurse':
            assert not any(row['kind']=='lab' or row['fields'].get('domain')=='D37' for row in rows)
        if has_lab:
            row=next(r for r in rows if r['kind']=='lab')
            assert row['fields']['result']=='Fasting plasma glucose: 152 mg/dL (70-99)'

def test_records_does_not_select_content_or_hidden_authors_and_nurse_never_selects_labs():
    statements=[]
    def before(conn,cursor,statement,parameters,context,executemany):statements.append(statement.lower())
    with SessionLocal.begin() as db:
        pid,eid,_=context(db);a=actor(db,'registration')
        event.listen(engine,'before_cursor_execute',before)
        try:collect_packet(db,a,'records_readiness',pid,eid)
        finally:event.remove(engine,'before_cursor_execute',before)
        selects=[q for q in statements if q.startswith('select')]
        assert not any('document_versions.content,' in q or 'document_versions.created_by' in q for q in selects)
        statements.clear();a=actor(db,'nurse')
        event.listen(engine,'before_cursor_execute',before)
        try:collect_packet(db,a,'nursing_handover',pid,eid)
        finally:event.remove(engine,'before_cursor_execute',before)
        assert not any('clinical_labs' in q for q in statements)

@pytest.mark.parametrize('role,profile', [('patient','visit_preparation'),('system_admin','visit_preparation'),('auditor','visit_preparation'),('nurse','visit_preparation'),('registration','laboratory_handoff')])
def test_ungranted_profiles_denied(role,profile):
    with SessionLocal.begin() as db:
        a=actor(db,role)
        with pytest.raises(HTTPException) as rejected:collect_packet(db,a,profile,'patient-001','encounter-001')
        assert rejected.value.status_code==403

@pytest.mark.parametrize('pid,eid',[('patient-other','encounter-other'),('patient-second','encounter-second'),('patient-001','encounter-002')])
def test_wrong_patient_facility_organization_context_denied(pid,eid):
    with SessionLocal.begin() as db:
        a=actor(db)
        with pytest.raises(HTTPException) as rejected:collect_packet(db,a,'visit_preparation',pid,eid)
        assert rejected.value.status_code==404

def test_worker_persists_preparation_without_domain_effects_and_get_never_dispatches():
    a,rid,pid,eid,_=fixture_run()
    calls=[]
    def prepare(*args):calls.append(1);return provider(*args)
    result=dispatch(prepare)
    assert result=={'dispatched':1,'run_id':rid,'state':'succeeded'} and len(calls)==1
    with SessionLocal.begin() as db:
        run=db.get(AssistantRun,rid);dto=run_dto(db,a,run)
        assert dto['review_state']=='pending' and dto['source_freshness']=='current' and dto['measured_cost'] is None
        assert db.scalar(select(func.count()).select_from(AssistantEffect).where(AssistantEffect.run_id==rid))==0
        for _ in range(3):run_dto(db,a,run)
        assert len(calls)==1

def test_apply_is_atomic_creates_only_draft_and_reuses_existing_open_task():
    a,rid,pid,eid,_=fixture_run();dispatch()
    with SessionLocal.begin() as db:
        existing=M.Task(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id=pid,encounter_id=eid,domain='D37',kind='document_review',title='Existing appropriate task')
        db.add(existing);db.flush()
    # This real source change makes the old artifact stale; no write may occur.
    with SessionLocal.begin() as db:
        with pytest.raises(HTTPException):apply_run(db,a,rid,apply_body(db,a,rid))
        assert db.scalar(select(func.count()).select_from(AssistantDecision).where(AssistantDecision.run_id==rid))==0
    with SessionLocal.begin() as db:
        new,_=enqueue(db,a,'visit_preparation',pid,eid,'en',uid());rid=new.id
    dispatch()
    with SessionLocal.begin() as db:
        response=apply_run(db,a,rid,apply_body(db,a,rid,edited='Human revised draft with professional additions 123.'))
        assert response['run']['review_state']=='accepted'
        doc_effect=next(e for e in response['effects'] if e['document_id'])
        task_effect=next(e for e in response['effects'] if e['task_id'])
        assert task_effect['task_id']==existing.id and not task_effect['receipt']['created']
        doc=db.get(M.Document,doc_effect['document_id']);revision=db.get(M.DocumentVersion,doc.current_version_id)
        assert doc.status=='draft' and not doc.published and revision.content=='Human revised draft with professional additions 123.'
        assert response['run']['revision']['origin']=='human'
        assert not db.scalar(select(M.DocumentAttestation.id).where(M.DocumentAttestation.document_version_id==revision.id))
    with SessionLocal.begin() as db:
        with pytest.raises(HTTPException) as rejected:apply_run(db,a,rid,apply_body(db,a,rid))
        assert rejected.value.status_code==409
        assert db.scalar(select(func.count()).select_from(AssistantEffect).where(AssistantEffect.run_id==rid))==2

def test_effects_roll_back_if_second_domain_permission_is_missing(monkeypatch):
    a,rid,_,_,_=fixture_run();dispatch()
    import backend.app.assistant_effects as effects
    original=effects.create_task
    def reject(*args,**kwargs):raise HTTPException(409,detail={'code':'INJECTED_TRANSACTION_FAILURE'})
    monkeypatch.setattr(effects,'create_task',reject)
    with pytest.raises(HTTPException):
        with SessionLocal.begin() as db:apply_run(db,a,rid,apply_body(db,a,rid))
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AssistantEffect).where(AssistantEffect.run_id==rid))==0
        assert db.scalar(select(func.count()).select_from(AssistantDecision).where(AssistantDecision.run_id==rid))==0
        assert db.get(AssistantRun,rid).review_state=='pending'

@pytest.mark.parametrize('change',['document','lab','care','session'])
def test_inflight_source_and_authorization_changes_reject_output(change):
    a,rid,pid,eid,did=fixture_run()
    def changed(profile,locale,view):
        with SessionLocal.begin() as db:
            db.execute(text("SET LOCAL lock_timeout='2s'"))
            if change=='document':
                doc=db.get(M.Document,did);doc.version+=1
                v=M.DocumentVersion(id=uid(),document_id=did,version=doc.version,content='Changed source',content_hash=text_hash('Changed source'),created_by=a.user_id)
                db.add(v);db.flush();doc.current_version_id=v.id
            elif change=='lab':
                lab=db.scalar(select(LabRequest).where(LabRequest.encounter_id==eid));lab.result_value='155';lab.status='corrected';lab.version+=1
            elif change=='care':db.get(M.CareAssignment,(a.user_id,pid)).active=False
            else:db.get(M.SessionRecord,a.session_id).revoked_at=utcnow()
        return provider(profile,locale,view)
    result=dispatch(changed)
    assert result['state']=='stale_context'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AssistantRevision).where(AssistantRevision.run_id==rid))==0
        assert db.get(AssistantRun,rid).provider['provider_outcome']=='success'

def test_concurrent_dispatch_and_same_source_request_call_once():
    a,rid,pid,eid,_=fixture_run();started=Event();release=Event();calls=[]
    def slow(*args):calls.append(1);started.set();assert release.wait(5);return provider(*args)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=pool.submit(dispatch,slow);assert started.wait(5)
        assert dispatch()['dispatched']==0
        with SessionLocal.begin() as db:
            same,reused=enqueue(db,a,'visit_preparation',pid,eid,'en',uid())
            assert same.id==rid and reused
        release.set();assert future.result()['state']=='succeeded'
    assert len(calls)==1

def test_legacy_and_assistant_share_admission_fence_in_both_directions():
    a,rid,pid,eid,_=fixture_run()
    with SessionLocal.begin() as db:
        legacy=M.InferenceRun(id=uid(),task_id='task-patient-001',actor_id=a.user_id,provider='ollama_legacy',outcome='running',elapsed_ms=0,context_snapshot={'lease_seconds':360})
        db.add(legacy);db.flush();legacy_id=legacy.id
    assert dispatch()['dispatched']==0
    with SessionLocal.begin() as db:
        assert db.get(AssistantRun,rid).execution_state=='waiting_for_capacity'
        old=db.get(M.InferenceRun,legacy_id);old.outcome='failed';old.completed_at=utcnow()
    started=Event();release=Event()
    def slow(*args):started.set();assert release.wait(5);return provider(*args)
    with ThreadPoolExecutor() as pool:
        future=pool.submit(dispatch,slow);assert started.wait(5)
        with SessionLocal.begin() as db:assert admission_busy(db)
        release.set();assert future.result()['state']=='succeeded'

def test_timeout_retained_deduplicated_and_holds_shared_slot():
    a,rid,pid,eid,_=fixture_run()
    def timed(*args):return {'outcome':'timeout','reason':'MODEL_TIMEOUT','artifact':None,'provenance':{'observed':True},'usage':None}
    assert dispatch(timed)['state']=='timeout'
    with SessionLocal.begin() as db:
        same,reused=enqueue(db,a,'visit_preparation',pid,eid,'en',uid());assert reused and same.id==rid
        assert admission_busy(db)
    # Move other tests past the timeout hold without deleting its immutable record.
    with SessionLocal.begin() as db:db.get(AssistantRun,rid).hold_until=utcnow()-timedelta(seconds=1)

def test_timed_out_remote_call_retains_hold_even_when_source_becomes_stale():
    a,rid,pid,eid,did=fixture_run()
    def timed(*args):
        with SessionLocal.begin() as db:db.get(M.Document,did).title='Changed during timed-out remote job'
        return {'outcome':'timeout','reason':'MODEL_TIMEOUT','artifact':None,'provenance':{},'usage':None}
    assert dispatch(timed)['state']=='stale_context'
    with SessionLocal.begin() as db:
        assert admission_busy(db)
        db.get(AssistantRun,rid).hold_until=utcnow()-timedelta(seconds=1)

@pytest.mark.parametrize('outcome',['failed','invalid_output','abstained'])
def test_failures_retained_without_revision(outcome):
    a,rid,_,_,_=fixture_run()
    def failure(*args):return {'outcome':outcome,'reason':'FIXED_TEST_REASON','artifact':None,'provenance':{},'usage':None}
    assert dispatch(failure)['state']==outcome
    with SessionLocal() as db:assert not db.scalar(select(AssistantRevision.id).where(AssistantRevision.run_id==rid))

def test_invalid_artifact_is_persisted_not_silently_repaired():
    _,rid,_,_,_=fixture_run()
    def invalid(*args):raise ValueError('INVALID_QUOTE')
    assert dispatch(validate=invalid)['state']=='invalid_output'
    with SessionLocal() as db:assert db.get(AssistantRun,rid).error=='ASSISTANT_ARTIFACT_INVALID'

def test_watch_unchanged_zero_calls_changed_once_coalesced_and_feedback_excluded():
    a,rid,pid,eid,did=fixture_run();dispatch()
    with SessionLocal.begin() as db:
        before=collect_packet(db,a,'visit_preparation',pid,eid)
        nurse=actor(db,'nurse');nbefore=collect_packet(db,nurse,'nursing_handover',pid,eid)
        watch=create_watch(db,a,'visit_preparation',pid,eid,'en',last_run=db.get(AssistantRun,rid));wid=watch.id
        response=apply_run(db,a,rid,apply_body(db,a,rid))
        created_doc=next(e['document_id'] for e in response['effects'] if e['document_id'])
        assert collect_packet(db,a,'visit_preparation',pid,eid)['source_digest']==before['source_digest']
        assert collect_packet(db,nurse,'nursing_handover',pid,eid)['source_digest']==nbefore['source_digest']
        generated=db.get(M.Document,created_doc);generated.status='in_review';generated.version+=1;db.flush()
        assert collect_packet(db,a,'visit_preparation',pid,eid)['source_digest']==before['source_digest']
    future=utcnow()+timedelta(seconds=70)
    assert scan_watches_once(now=future)['enqueued']==0
    with SessionLocal.begin() as db:
        doc=db.get(M.Document,created_doc);doc.version+=1;doc.status='draft'
        v=M.DocumentVersion(id=uid(),document_id=doc.id,version=doc.version,content='Human reviewed added history',content_hash=text_hash('Human reviewed added history'),created_by=a.user_id)
        db.add(v);db.flush();doc.current_version_id=v.id
        assert collect_packet(db,nurse,'nursing_handover',pid,eid)['source_digest']!=nbefore['source_digest']
    future+=timedelta(seconds=31)
    assert scan_watches_once(now=future)['enqueued']==1
    assert scan_watches_once(now=future+timedelta(seconds=31))['enqueued']==0
    with SessionLocal() as db:
        assert db.get(AssistantWatch,wid).auto_run_count==1
        assert db.scalar(select(func.count()).select_from(AssistantRun).where(AssistantRun.encounter_id==eid,AssistantRun.execution_state.in_(['queued','waiting_for_capacity'])))==1
    dispatch()

@pytest.mark.parametrize('stop',['paused','expiry','session','scope'])
def test_watch_pause_expiry_revocation_prevent_enqueues(stop):
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);a=actor(db)
        w=create_watch(db,a,'visit_preparation',pid,eid);wid=w.id
        if stop=='paused':w.status='paused'
        elif stop=='session':db.get(M.SessionRecord,a.session_id).revoked_at=utcnow()
        elif stop=='scope':db.get(M.CareAssignment,(a.user_id,pid)).active=False
        db.get(M.Document,did).title='Human metadata change'
    result=scan_watches_once(now=utcnow()+timedelta(minutes=31 if stop=='expiry' else 2))
    assert result['enqueued']==0
    with SessionLocal() as db:
        assert db.get(AssistantWatch,wid).status in ('paused','expired','revoked')

def test_queued_job_revalidates_session_and_never_replays_on_restart():
    a,rid,_,_,_=fixture_run()
    with SessionLocal.begin() as db:db.get(M.SessionRecord,a.session_id).revoked_at=utcnow()
    calls=[]
    def forbidden(*args):calls.append(1);return provider(*args)
    assert dispatch(forbidden)['dispatched']==0 and dispatch(forbidden)['dispatched']==0 and calls==[]
    with SessionLocal() as db:assert db.get(AssistantRun,rid).execution_state=='stale_context'

def test_profile_qualification_is_explicit():
    _,rid,_,_,_=fixture_run()
    calls=[]
    def forbidden(*args):calls.append(1);return provider(*args)
    assert dispatch(forbidden,config={**CONFIG,'profiles_qualified':[]})['dispatched']==0 and calls==[]
    with SessionLocal() as db:assert db.get(AssistantRun,rid).error=='ASSISTANT_PROVIDER_NOT_QUALIFIED'

def login(role='clinician'):
    c=TestClient(app);r=c.post('/api/v2/auth/login',json={'username':role,'password':os.environ['HIS_SEED_PASSWORD']});assert r.status_code==200
    c.headers['X-CSRF-Token']=r.json()['csrf_token'];return c

def test_api_scope_idempotency_apply_and_operations_map(monkeypatch):
    from backend.app import assistant_api
    monkeypatch.setattr(assistant_api,'_provider_config',lambda:CONFIG)
    with SessionLocal.begin() as db:pid,eid,_=context(db)
    c=login();key=uid();body={'profile':'visit_preparation','patient_id':pid,'encounter_id':eid}
    response=c.post('/api/v2/assistant/runs',json=body,headers={'Idempotency-Key':key});assert response.status_code==202,response.text
    rid=response.json()['run']['id']
    assert c.post('/api/v2/assistant/runs',json=body,headers={'Idempotency-Key':key}).json()['run']['id']==rid
    assert c.get('/api/v2/assistant/config').json()['default_profile']=='visit_preparation'
    assert dispatch()['run_id']==rid
    run=c.get('/api/v2/assistant/runs/'+rid).json();rev=run['revision']
    payload={'expected_revision_id':rev['id'],'expected_version':rev['version'],'expected_content_hash':rev['content_hash'],'expected_source_digest':run['source_digest'],'selected_action_ids':[a['action_id'] for a in rev['suggested_effects']]}
    applykey=uid();response=c.post('/api/v2/assistant/runs/'+rid+'/apply',json=payload,headers={'Idempotency-Key':applykey});assert response.status_code==200,response.text
    assert c.post('/api/v2/assistant/runs/'+rid+'/apply',json=payload,headers={'Idempotency-Key':applykey}).json()==response.json()
    assert c.post('/api/v2/assistant/runs/'+rid+'/apply',json=payload,headers={'Idempotency-Key':uid()}).status_code==409
    nurse=login('nurse');ops=nurse.get('/api/v2/assistant/operations-map').json()
    assert next(z for z in ops['zones'] if z['id']=='laboratory')['open_task_count'] is None
    assert next(z for z in ops['zones'] if z['id']=='nursing')['available']
    assert nurse.get('/api/v2/assistant/runs/'+rid).status_code==404
    assert login('patient').get('/api/v2/assistant/worklist').status_code==403

def test_database_preserves_immutable_assistant_evidence():
    a,rid,_,_,_=fixture_run();dispatch()
    with SessionLocal.begin() as db:revision=db.scalar(select(AssistantRevision).where(AssistantRevision.run_id==rid));revision_id=revision.id
    with SessionLocal() as db:
        with pytest.raises(Exception):db.execute(text('UPDATE assistant_revisions SET artifact=:artifact WHERE id=:id'),{'artifact':'{}','id':revision_id});db.commit()
        db.rollback()
        with pytest.raises(Exception):db.execute(text('DELETE FROM assistant_runs WHERE id=:id'),{'id':rid});db.commit()
        db.rollback()

def test_concurrent_different_keys_cannot_duplicate_effects():
    a,rid,_,_,_=fixture_run();dispatch()
    with SessionLocal() as db:body=apply_body(db,a,rid)
    def submit():
        try:
            with SessionLocal.begin() as db:return apply_run(db,a,rid,body)['decision_id']
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:submit(),range(2)))
    assert sum(isinstance(r,str) for r in results)==1 and results.count(409)==1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AssistantDecision).where(AssistantDecision.run_id==rid))==1
        assert db.scalar(select(func.count()).select_from(AssistantEffect).where(AssistantEffect.run_id==rid))==2

def test_watch_coalesces_changed_sources_and_caps_three_auto_runs():
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);a=actor(db)
        watch=create_watch(db,a,'visit_preparation',pid,eid);wid=watch.id
    baseline=utcnow()
    for n in range(4):
        with SessionLocal.begin() as db:db.get(M.Document,did).title=f'Human metadata revision {n}'
        scan_watches_once(now=baseline+timedelta(seconds=70*(n+1)))
    with SessionLocal() as db:
        watch=db.get(AssistantWatch,wid)
        assert watch.auto_run_count==3 and watch.status=='exhausted'
        runs=db.scalars(select(AssistantRun).where(AssistantRun.encounter_id==eid).order_by(AssistantRun.created_at)).all()
        assert len(runs)==3
        assert [r.execution_state for r in runs]==['stale_context','stale_context','queued']
    # The final human change is newer than the capped queue packet: worker rejects it.
    assert dispatch()['dispatched']==0

def test_generated_task_human_state_change_becomes_eligible():
    a,rid,pid,eid,_=fixture_run();dispatch()
    with SessionLocal.begin() as db:
        before=collect_packet(db,a,'visit_preparation',pid,eid)['source_digest']
        result=apply_run(db,a,rid,apply_body(db,a,rid))
        tid=next(e['task_id'] for e in result['effects'] if e['task_id'])
        assert collect_packet(db,a,'visit_preparation',pid,eid)['source_digest']==before
        task=db.get(M.Task,tid);task.status='in_progress';task.version+=1;db.flush()
        assert collect_packet(db,a,'visit_preparation',pid,eid)['source_digest']!=before

def test_complete_note_omission_is_explicit_and_source_change_still_changes_digest():
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);a=actor(db)
        packet=collect_packet(db,a,'visit_preparation',pid,eid)
        doc=db.get(M.Document,did);doc.version+=1
        body='ข้อความสังเคราะห์ยาว'*1000
        revision=M.DocumentVersion(id=uid(),document_id=did,version=doc.version,content=body,content_hash=text_hash(body),created_by=a.user_id)
        db.add(revision);db.flush();doc.current_version_id=revision.id
        large=collect_packet(db,a,'visit_preparation',pid,eid)
        assert large['source_digest']!=packet['source_digest']
        assert large['view']['coverage']['omitted_sources']>=1
        assert not any(source.get('text') for source in large['view']['sources'])
        assert next(s for s in large['manifest']['sources'] if s['kind']=='document')['text']==body

def test_actual_legacy_route_refuses_call_while_assistant_running():
    from backend.app import ai
    a,rid,pid,eid,did=fixture_run()
    started=Event();release=Event();legacy_calls=[]
    class LegacyProvider:
        name='offline_live_provider';is_live=True;timeout_seconds=2
        def public_config(self):return {'provider':self.name}
        def generate_document(self,*args):legacy_calls.append(1);raise AssertionError('legacy must not call')
    def slow(*args):started.set();assert release.wait(5);return provider(*args)
    with ThreadPoolExecutor() as pool:
        future=pool.submit(dispatch,slow);assert started.wait(5)
        with SessionLocal.begin() as db:
            # A separate encounter prevents stale-by-new-task from hiding admission behavior.
            body=ai.Propose(task_id='task-patient-001',document_id='document-patient-001')
            t=db.get(M.Task,body.task_id);d=db.get(M.Document,body.document_id);v=db.get(M.DocumentVersion,d.current_version_id);e=db.get(M.Encounter,t.encounter_id)
            response=ai.live_propose(db,a,body,uid(),body.model_dump(),LegacyProvider(),t,d,e,v)
            assert response['run']['reason']=='LIVE_PROVIDER_BUSY' and response['proposal'] is None
        release.set();assert future.result()['state']=='succeeded'
    assert legacy_calls==[]

@pytest.mark.parametrize('role,profile,domains,documents',[
    ('clinician','visit_preparation',{'D22','D37'},1),('nurse','nursing_handover',{'D22','D06'},1),('registration','records_readiness',{'D01'},0),('laboratory','laboratory_handoff',{'D10'},0)])
def test_all_four_profiles_prepare_then_apply_only_permitted_drafts_tasks(role,profile,domains,documents):
    a,rid,pid,eid,_=fixture_run(profile,role)
    with SessionLocal() as db:
        orders_before=db.scalar(select(func.count()).select_from(M.ClinicalOrder).where(M.ClinicalOrder.encounter_id==eid))
        lab_before=[(r.id,r.status,r.version,r.result_value,r.acknowledged_by) for r in db.scalars(select(LabRequest).where(LabRequest.encounter_id==eid))]
    assert dispatch()['state']=='succeeded'
    with SessionLocal.begin() as db:
        result=apply_run(db,a,rid,apply_body(db,a,rid))
        assert {e['domain'] for e in result['effects']}==domains
        assert sum(bool(e['document_id']) for e in result['effects'])==documents
        assert all(not e['document_id'] or db.get(M.Document,e['document_id']).status=='draft' for e in result['effects'])
        assert db.scalar(select(func.count()).select_from(M.ClinicalOrder).where(M.ClinicalOrder.encounter_id==eid))==orders_before
        assert [(r.id,r.status,r.version,r.result_value,r.acknowledged_by) for r in db.scalars(select(LabRequest).where(LabRequest.encounter_id==eid))]==lab_before
        if role=='registration':assert result['run']['revision']['drafts']==[]

def test_queue_and_active_watch_caps_are_six_and_revocation_drains_without_dispatch():
    with SessionLocal.begin() as db:
        contexts=[context(db) for _ in range(7)];a=actor(db)
        for pid,eid,did in contexts[:6]:
            enqueue(db,a,'visit_preparation',pid,eid,'en',uid())
            create_watch(db,a,'visit_preparation',pid,eid)
        pid,eid,_=contexts[6]
        with pytest.raises(HTTPException) as queue_error:enqueue(db,a,'visit_preparation',pid,eid,'en',uid())
        assert queue_error.value.status_code==429
        with pytest.raises(HTTPException) as watch_error:create_watch(db,a,'visit_preparation',pid,eid)
        assert watch_error.value.status_code==429
        db.get(M.SessionRecord,a.session_id).revoked_at=utcnow()
    assert dispatch()['dispatched']==0
    assert scan_watches_once(now=utcnow()+timedelta(minutes=2))['revoked']==6
    with SessionLocal() as db:
        assert not db.scalar(select(AssistantRun.id).where(AssistantRun.session_id==a.session_id,AssistantRun.execution_state.in_(['queued','running','waiting_for_capacity'])))

def test_missing_d22_write_removes_draft_candidate_without_role_inference():
    with SessionLocal.begin() as db:
        pid,eid,_=context(db);a=actor(db);a.permissions.remove('D22.write')
        packet=collect_packet(db,a,'visit_preparation',pid,eid)
        assert [c['kind'] for c in packet['view']['effect_candidates']]==['create_document_review_task']

def test_read_render_endpoints_do_not_create_runs_or_watches(monkeypatch):
    from backend.app import assistant_api
    monkeypatch.setattr(assistant_api,'_provider_config',lambda:CONFIG)
    c=login('nurse')
    with SessionLocal() as db:
        counts=(db.scalar(select(func.count()).select_from(AssistantRun)),db.scalar(select(func.count()).select_from(AssistantWatch)))
    for route in ('config','worklist','watches','operations-map'):
        for _ in range(2):assert c.get('/api/v2/assistant/'+route).status_code==200
    with SessionLocal() as db:assert counts==(db.scalar(select(func.count()).select_from(AssistantRun)),db.scalar(select(func.count()).select_from(AssistantWatch)))

def test_terminal_visits_are_absent_from_eligible_work_and_do_not_abort_batch():
    with SessionLocal.begin() as db:
        pid,active_eid,_=context(db)
        terminal_ids=[]
        for status in ('closed','completed','discharged','cancelled'):
            _,eid,_=context(db);visit=db.get(M.Encounter,eid);visit.status=status;visit.version+=1;terminal_ids.append(eid)
    c=login()
    work=c.get('/api/v2/assistant/worklist',params={'profile':'visit_preparation'})
    assert work.status_code==200
    eligible={item['encounter_id'] for item in work.json()['eligible_contexts']}
    assert active_eid in eligible and not eligible.intersection(terminal_ids)
    response=c.post('/api/v2/assistant/batches',json={'profile':'visit_preparation','maximum_contexts':1,'keep_prepared':False},headers={'Idempotency-Key':uid()})
    assert response.status_code==202,response.text
    assert [run['encounter_id'] for run in response.json()['runs']]==[active_eid]
    assert c.post('/api/v2/auth/logout').status_code==200
    assert dispatch()['dispatched']==0

def test_disabled_assistant_flag_keeps_role_capability_metadata_but_disables_home(monkeypatch):
    from backend.app import assistant_api
    calls=[]
    def disabled_config():calls.append(1);return {**CONFIG,'enabled':False}
    monkeypatch.setattr(assistant_api,'_provider_config',disabled_config)
    response=login().get('/api/v2/assistant/config')
    assert response.status_code==200
    data=response.json()
    assert data['enabled'] is False and data['provider']['enabled'] is False
    assert next(p for p in data['profiles'] if p['id']=='visit_preparation')['available'] is True
    assert data['default_profile']=='visit_preparation' and calls==[1]

def test_worker_lease_clock_refreshes_after_delayed_authorization_and_admission():
    a,rid,_,_,_=fixture_run()
    entry=utcnow()-timedelta(minutes=10);reserved=utcnow()
    times={'current':entry};calls=[]
    def after_collection_config():
        # Simulate a lock/collection wait longer than the entire old reservation.
        times['current']=reserved
        return CONFIG
    def prepared(*args):
        with SessionLocal() as db:
            run=db.get(AssistantRun,rid)
            assert run.started_at==reserved
            assert run.lease_expires_at==reserved+timedelta(seconds=62)
            assert run.hold_until==reserved+timedelta(seconds=122)
            assert run.lease_expires_at>utcnow()
        calls.append(1)
        return provider(*args)
    result=run_once(prepare=prepared,validate=lambda p,a,v:a,config=after_collection_config,clock=lambda:times['current'])
    assert result['state']=='succeeded' and calls==[1]

def test_admission_clock_is_read_only_after_global_lock_acquisition(monkeypatch):
    from backend.app import assistant_admission
    observed=[]
    with SessionLocal.begin() as db:
        original=db.execute
        def execute(statement,*args,**kwargs):
            result=original(statement,*args,**kwargs)
            if 'pg_advisory_xact_lock' in str(statement):observed.append('lock_acquired')
            return result
        def after_lock_clock():
            assert observed==['lock_acquired']
            observed.append('clock_read')
            return utcnow()
        monkeypatch.setattr(db,'execute',execute)
        monkeypatch.setattr(assistant_admission,'utcnow',after_lock_clock)
        assert not admission_busy(db)
    assert observed==['lock_acquired','clock_read']

def test_legacy_new_run_lease_starts_after_delayed_global_admission(monkeypatch):
    from backend.app import ai, assistant_admission
    from sqlalchemy.orm import Session
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);a=actor(db)
        task=M.Task(id=uid(),organization_id=a.organization_id,facility_id=a.facility_id,patient_id=pid,encounter_id=eid,domain='D37',kind='document_review',title='Synthetic legacy admission test')
        db.add(task);db.flush();task_id=task.id
    key=uid();entry=utcnow()-timedelta(minutes=10);reserved=utcnow();clock={'value':entry};calls=[]
    original=assistant_admission.admission_busy
    def delayed_admission(db,**kwargs):
        busy=original(db,**kwargs)
        clock['value']=reserved
        return busy
    def assign_logical_created_at(session,flush_context,instances):
        for row in session.new:
            if isinstance(row,M.InferenceRun) and row.operation_key==key:row.created_at=clock['value']
    class LegacyProvider:
        name='offline_delayed_legacy';is_live=True;timeout_seconds=2
        def public_config(self):return {'provider':self.name,'test_double':True}
        def generate_document(self,*args):
            with SessionLocal() as db:
                persisted=db.scalar(select(M.InferenceRun).where(M.InferenceRun.operation_key==key))
                assert persisted.created_at==reserved
                assert persisted.created_at+timedelta(seconds=persisted.context_snapshot['lease_seconds'])>utcnow()
            calls.append(1)
            return {'outcome':'success','reason':None,'action':{'text':'Synthetic professional review','completeness':{}},'provenance':{'test_double':True},'usage':None}
    monkeypatch.setattr(assistant_admission,'admission_busy',delayed_admission)
    event.listen(Session,'before_flush',assign_logical_created_at)
    try:
        with SessionLocal() as db:
            task=db.get(M.Task,task_id);doc=db.get(M.Document,did);visit=db.get(M.Encounter,eid);revision=db.get(M.DocumentVersion,doc.current_version_id)
            body=ai.Propose(task_id=task_id,document_id=did)
            result=ai.live_propose(db,a,body,key,body.model_dump(),LegacyProvider(),task,doc,visit,revision)
            assert result['run']['outcome']=='success' and result['proposal'] is not None
    finally:event.remove(Session,'before_flush',assign_logical_created_at)
    assert calls==[1]
