"""New selector versus frozen released collector, with actual disposable PG18."""
import hashlib
import os
from datetime import timedelta, date
from pathlib import Path
from types import ModuleType
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, event

assert os.environ.get('HIS_TEST_DATABASE_URL') == os.environ.get('DATABASE_URL') and os.environ.get('HIS_TEST_DATABASE_URL')
from backend.app import models as M
from backend.app.db import SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed
from backend.app.common import uid, utcnow, authorization_hash, text_hash, digest
from backend.app.assistant_collectors import collect_packet, _pristine
from backend.app.assistant_core import enqueue, create_watch
from backend.app.assistant_schema import validate_assistant_artifact
from backend.app.assistant_worker import scan_watches_once
from backend.app.models_assistant import AssistantRun, AssistantRevision, AssistantWatch, AssistantEffect
from backend.tests.test_assistant_pg import actor, context


@pytest.fixture(scope='module', autouse=True)
def seeded():
    assert engine.url.database == 'his_test'
    with SessionLocal.begin() as db: seed(db, os.environ['HIS_SEED_PASSWORD'])


def old_collector():
    raw = Path(__file__).with_name('fixtures').joinpath('assistant_collector_v1.py.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='d92670a61457cd2c719740f9bb113c74f37f19f3c4de4562e27277930240a961'
    # Exact released source, rather than a new implementation's reconstruction.
    module = ModuleType('frozen_v1'); module.__package__ = 'backend.app'
    exec(compile(raw, 'released-c47868a-collector', 'exec'), module.__dict__)
    return module.collect_packet, hashlib.sha256(raw).hexdigest()


def long_context(db):
    pid,eid,did,vid=uid(),uid(),uid(),uid()
    common={'organization_id':'org-demo','facility_id':'facility-demo'}
    db.add(M.Patient(id=pid,**common,display_name='กมลชนก ศรีสาธิต',birth_date=date(1968,2,13),sex='female',status='active'));db.flush()
    db.add(M.Encounter(id=eid,patient_id=pid,**common,status='in_consult'));db.flush()
    for role in ('clinician','nurse'):db.add(M.CareAssignment(user_id='user-'+role,patient_id=pid))
    db.add(M.Document(id=did,patient_id=pid,encounter_id=eid,**common,title='Clinical source',version=1));db.flush()
    text='Administrative cover information.\n'*80+'History: fictional cough for three days. No medicine changes recorded.\nPending: bring the earlier note for review.'
    db.add(M.DocumentVersion(id=vid,document_id=did,version=1,content=text,content_hash=text_hash(text),created_by='user-clinician'));db.flush();db.get(M.Document,did).current_version_id=vid
    task = M.Task(id=uid(), organization_id='org-demo', facility_id='facility-demo', patient_id=pid, encounter_id=eid, domain='D37', kind='document_review', title='Review the fictional source', status='open')
    db.add(task); db.flush()
    return pid, eid, did, task.id


def client_for(role='clinician'):
    client = TestClient(app)
    response = client.post('/api/v2/auth/login', json={'username':role,'password':os.environ['HIS_SEED_PASSWORD']})
    assert response.status_code == 200
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return client


def test_long_source_passage_is_selected_and_original_digest_unchanged():
    collect_v1, sha = old_collector(); assert len(sha) == 64
    with SessionLocal.begin() as db:
        pid,eid,did,tid = long_context(db); a = actor(db)
        old = collect_v1(db,a,'visit_preparation',pid,eid,'en')
        new = collect_packet(db,a,'visit_preparation',pid,eid,'en')
        assert old['source_digest'] == new['source_digest']
        assert old['input_hash'] != new['input_hash']
        assert not any(s['kind']=='document' for s in old['view']['sources'])
        assert new['view']['sources'][0]['kind']=='document'
        assert 'fictional cough for three days' in new['view']['sources'][0]['text']
        full = next(s for s in new['manifest']['sources'] if s['id']==did)
        selection=full['selection']; assert selection['kind']=='excerpt'
        assert full['text'][selection['start']:selection['end']] == new['view']['sources'][0]['text']
        assert len(__import__('backend.app.common',fromlist=['canonical']).canonical(new['view']).encode())<=2000


def test_frozen_v1_watch_selector_only_and_operational_edits_do_not_enqueue():
    collect_v1, _ = old_collector()
    with SessionLocal.begin() as db:
        pid,eid,did,tid=long_context(db); a=actor(db)
        old=collect_v1(db,a,'visit_preparation',pid,eid,'en')
        old_run=AssistantRun(id=uid(),organization_id=a.organization_id,facility_id=a.facility_id,patient_id=pid,encounter_id=eid,actor_id=a.user_id,session_id=a.session_id,profile='visit_preparation',locale='en',authorization_hash=authorization_hash(a),operation_key=uid(),request_hash=uid(),source_digest=old['source_digest'],source_manifest=old['manifest'],inference_view=old['view'],input_hash=old['input_hash'],execution_state='succeeded',review_state='pending',provider={})
        old_run.request_hash=digest({'profile':'visit_preparation','patient_id':pid,'encounter_id':eid,'locale':'en','expected_source_digest':None})
        db.add(old_run);db.flush();original_key=old_run.operation_key
        watch=create_watch(db,a,'visit_preparation',pid,eid,'en',30,old_run)
        watch.next_scan_at=utcnow()-timedelta(seconds=1);watch.last_enqueued_at=utcnow()-timedelta(minutes=2)
        wid=watch.id; old_id=old_run.id
        task=db.get(M.Task,tid);task.assignee_id=a.user_id;task.version+=1
        db.add(M.TaskCoordination(task_id=tid,operational_updates=1,priority='high',due_at=utcnow()-timedelta(minutes=5)))
        db.flush();assert collect_packet(db,a,'visit_preparation',pid,eid,'en')['source_digest']==old['source_digest']
    scan_watches_once()
    with SessionLocal.begin() as db:
        w=db.get(AssistantWatch,wid);assert w.auto_run_count==0 and w.last_run_id==old_id
        a=actor(db);replayed,reused=enqueue(db,a,'visit_preparation',pid,eid,'en',original_key)
        assert reused and replayed.id==old_id
        # A fresh explicit request may improve the selector without a source edit.
        a=actor(db);improved,reused=enqueue(db,a,'visit_preparation',pid,eid,'en',uid())
        assert not reused and improved.id!=old_id and improved.input_hash!=old['input_hash']
        doc=db.get(M.Document,did);text='History: a genuinely changed authored note.';vid=uid()
        db.add(M.DocumentVersion(id=vid,document_id=did,version=2,content=text,content_hash=text_hash(text),created_by=a.user_id));db.flush();doc.current_version_id=vid;doc.version+=1
    scan_watches_once(now=utcnow()+timedelta(seconds=31))
    with SessionLocal.begin() as db:
        w=db.get(AssistantWatch,wid);assert w.auto_run_count==1 and w.last_run_id not in (old_id,improved.id)
        w.status='paused'


def test_ownership_does_not_turn_pristine_assistant_task_into_source():
    with SessionLocal.begin() as db:
        pid,eid,did,tid=long_context(db);a=actor(db)
        run,_=enqueue(db,a,'visit_preparation',pid,eid,'en',uid())
        task=db.get(M.Task,tid)
        revision=AssistantRevision(id=uid(),run_id=run.id,version=1,content_hash='a'*64,source_digest=run.source_digest,artifact={},origin='model',created_by=a.user_id);db.add(revision);db.flush()
        db.add(AssistantEffect(id=uid(),run_id=run.id,revision_id=revision.id,action_id='a1',kind='create_document_review_task',task_id=tid,receipt={'created':True,'version':task.version,'status':task.status,'title':task.title}));db.flush()
        assert _pristine(db,task,'task')
        task.version+=1;task.assignee_id=a.user_id;db.add(M.TaskCoordination(task_id=tid,operational_updates=1));db.flush()
        assert _pristine(db,task,'task')
        task.version+=1;task.status='in_progress';assert not _pristine(db,task,'task')


def test_exact_snapshot_survives_source_correction_and_denies_other_actor():
    with SessionLocal.begin() as db:
        pid,eid,did,tid=long_context(db);a=actor(db)
        run,_=enqueue(db,a,'visit_preparation',pid,eid,'en',uid());run.execution_state='succeeded';run.review_state='pending'
        source=next(s for s in run.inference_view['sources'] if s['kind']=='document');quoted=source['text'][:80]
        artifact=validate_assistant_artifact(run.profile,{'facts':[{'source_ref':source['ref'],'quote':quoted}],'work_gaps':[],'drafts':[],'suggested_effects':[],'requires_review':True},run.inference_view)
        revision=AssistantRevision(id=uid(),run_id=run.id,version=1,content_hash=digest(artifact),source_digest=run.source_digest,artifact=artifact,origin='model',created_by=a.user_id);db.add(revision);db.flush()
        rid=run.id;ref=source['ref'];original=deepcopy(next(s for s in run.source_manifest['sources'] if s.get('ref')==ref))
    client=client_for();response=client.get(f'/api/v2/assistant/runs/{rid}/sources/{ref}');assert response.status_code==200
    result=response.json();citation=result['citations'][0]
    assert result['text']==original['text'] and result['text'][citation['start']:citation['end']]==quoted
    assert result['content_hash']==text_hash(result['text']) and result['source_freshness']=='current'
    with SessionLocal.begin() as db:
        doc=db.get(M.Document,did);text='History: a new independently authored fictional correction.';vid=uid()
        db.add(M.DocumentVersion(id=vid,document_id=did,version=2,content=text,content_hash=text_hash(text),created_by='user-clinician'));db.flush();doc.current_version_id=vid;doc.version+=1
    corrected=client.get(f'/api/v2/assistant/runs/{rid}/sources/{ref}').json()
    assert corrected['text']==result['text'] and corrected['source_freshness']=='stale'
    assert client.get(f'/api/v2/assistant/runs/{rid}/sources/s999').status_code==404
    other=client_for('nurse');assert other.get(f'/api/v2/assistant/runs/{rid}/sources/{ref}').status_code==404
    with SessionLocal.begin() as db:
        assignment=db.scalar(select(M.CareAssignment).where(M.CareAssignment.user_id=='user-clinician',M.CareAssignment.patient_id==pid));assignment.active=False
    assert client.get(f'/api/v2/assistant/runs/{rid}/sources/{ref}').status_code in (403,404)


def test_records_snapshot_never_selects_or_returns_document_body():
    with SessionLocal.begin() as db:
        pid,eid,did,tid=long_context(db);a=actor(db,'registration')
        statements=[]
        def capture(conn,cursor,statement,params,context,executemany):statements.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        try:run,_=enqueue(db,a,'records_readiness',pid,eid,'en',uid())
        finally:event.remove(engine,'before_cursor_execute',capture)
        assert not any('document_versions.content ' in sql or 'document_versions.created_by' in sql for sql in statements)
        assert all('text' not in source for source in run.inference_view['sources'])
        ref=next(s['ref'] for s in run.source_manifest['sources'] if s['kind']=='document' and s.get('ref'));rid=run.id
    response=client_for('registration').get(f'/api/v2/assistant/runs/{rid}/sources/{ref}')
    assert response.status_code==200 and response.json()['text'] is None and response.json()['selected_excerpt'] is None
