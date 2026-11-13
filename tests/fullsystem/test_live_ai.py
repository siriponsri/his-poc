"""Real PostgreSQL acceptance of the live-provider transaction boundary.

The provider in this suite is deliberately injected, deterministic and local.
These tests prove orchestration/authorization/persistence, not dr-train access or
model quality. Actual remote-model/browser evidence is recorded separately.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, text

from backend.app import providers
from backend.app.auth import COOKIE
from backend.app.common import text_hash, utcnow
from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import (
    AuditEvent, CommittedResult, DocumentVersion, InferenceRun, Operation,
    Proposal, ProposalVersion, SessionRecord, Task, User,
)
from backend.app.seed import seed


CHECKLIST = 'SYNTHETIC_DOCUMENT_COMPLETENESS_V1'
CONTENT = ('อาการสำคัญ: ไอ\nประวัติ: อาการสามวัน\n'
           'การประเมิน: บันทึกโดยผู้ตรวจ\nแผน: นัดติดตาม\n'
           'ผู้บันทึก: ผู้ทดสอบสังเคราะห์')
ITEMS = [
    ('chief_complaint', 'อาการสำคัญ', 'อาการสำคัญ: ไอ'),
    ('history', 'ประวัติ', 'ประวัติ: อาการสามวัน'),
    ('assessment', 'การประเมิน', 'การประเมิน: บันทึกโดยผู้ตรวจ'),
    ('plan', 'แผน', 'แผน: นัดติดตาม'),
    ('author', 'ผู้บันทึก', 'ผู้บันทึก: ผู้ทดสอบสังเคราะห์'),
]
TRACE = []


def key():
    return str(uuid.uuid4())


def normalized_success():
    report = {
        'checklist_id': CHECKLIST,
        'items': [{'key': name, 'label': label, 'status': 'present',
                   'evidence_quote': quote} for name, label, quote in ITEMS],
        'summary': 'พบข้อมูลครบตามรายการตรวจ ต้องให้ผู้ตรวจยืนยันก่อนบันทึก',
        'requires_human_review': True,
    }
    return {
        'outcome': 'success', 'action': {'text': report['summary'], 'completeness': report},
        'reason': None, 'demo': False, 'provider': 'dr_train_ollama',
        'elapsed_ms': 17, 'measured_cost': None,
        'usage': {'prompt_eval_count': 101, 'eval_count': 71},
        'provenance': {'provider': 'dr_train_ollama', 'model': 'synthetic-typhoon',
                       'model_digest': 'a' * 64, 'engine': 'ollama',
                       'engine_version': '0.12.6', 'checklist_id': CHECKLIST,
                       'prompt_sha256': 'b' * 64, 'schema_sha256': 'c' * 64},
    }


class FakeLiveProvider:
    """Injected provider; never opens a network connection."""
    is_live = True
    demo = False
    name = 'dr_train_ollama'
    model = 'synthetic-typhoon'
    model_digest = 'a' * 64
    timeout_seconds = 10
    timeout = 10
    max_output_tokens = 768
    context_tokens = 4096

    def __init__(self, callback=None, outcome=None):
        self.callback = callback
        self.response = outcome if outcome is not None else normalized_success()
        self.calls = []
        self._lock = threading.Lock()

    def public_config(self):
        return {'active_provider': self.name, 'demo': False, 'live_routes_enabled': True,
                'model': self.model, 'model_digest': self.model_digest,
                'supported_task_kinds': ['document_review'], 'checklist_id': CHECKLIST}

    def generate_document(self, title, content, checklist_id=CHECKLIST):
        with self._lock:
            self.calls.append({'title': title, 'content': content, 'checklist_id': checklist_id})
        if self.callback:
            self.callback()
        return deepcopy(self.response)


@pytest.fixture(scope='module', autouse=True)
def synthetic_postgres():
    if not os.getenv('HIS_TEST_DATABASE_URL'):
        pytest.skip('Run only with the disposable PostgreSQL wrapper')
    command.upgrade(Config('backend/alembic.ini'), 'head')
    with SessionLocal.begin() as db:
        seed(db, os.environ['HIS_SEED_PASSWORD'])
    yield
    root = Path('evidence/fullsystem/live-ai')
    root.mkdir(parents=True, exist_ok=True)
    paths = [Path(__file__), Path('backend/app/ai.py'), Path('backend/app/models.py')]
    result = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'method': 'INJECTED_PROVIDER_WITH_ACTUAL_POSTGRESQL',
              'remote_inference': 'NOT_RUN_BY_THIS_SUITE',
              'completed_assertion_records': TRACE,
              'source_sha256': {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in paths}}
    (root/'pg-test-records.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',
                                          encoding='utf-8')


@contextmanager
def login(username='clinician'):
    with TestClient(app) as client:
        response = client.post('/api/v2/auth/login', json={
            'username': username, 'password': os.environ['HIS_SEED_PASSWORD']})
        assert response.status_code == 200, response.text
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        yield client


@contextmanager
def cloned(client):
    with TestClient(app) as other:
        other.cookies.update(dict(client.cookies))
        other.headers.update(dict(client.headers))
        yield other


def post(client, path, body, expected=200, operation_key=None):
    response = client.post('/api/v2'+path, json=body,
                           headers={'Idempotency-Key': operation_key or key()})
    assert response.status_code == expected, (path, response.status_code, response.text)
    return response.json()


def subject(client, kind='document_review', encounter_id='encounter-001'):
    document = post(client, '/documents', {
        'patient_id': 'patient-001', 'encounter_id': encounter_id,
        'title': 'Synthetic live review '+key(), 'content': CONTENT}, 201)
    task = post(client, '/tasks', {
        'patient_id': 'patient-001', 'encounter_id': encounter_id,
        'domain': 'D37', 'kind': kind, 'title': 'Synthetic completeness '+key()}, 201)
    return document, task, {'document_id': document['id'], 'task_id': task['id']}


def install(monkeypatch, provider):
    monkeypatch.setenv('HIS_AI_PROVIDER', 'dr_train_ollama')
    monkeypatch.setenv('HIS_LIVE_SYNTHETIC_ENABLED', 'true')
    monkeypatch.setattr(providers, 'resolve_provider', lambda: provider)


def no_proposal(task_id):
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Proposal).where(
            Proposal.task_id == task_id)) == 0
        assert db.scalar(select(func.count()).select_from(CommittedResult).where(
            CommittedResult.task_id == task_id)) == 0
        assert db.get(Task, task_id).status == 'open'


def test_live_content_outside_transaction_and_completed_idempotency(monkeypatch):
    observations = []

    def outside_transaction():
        with SessionLocal.begin() as db:
            db.execute(text("SET LOCAL lock_timeout = '500ms'"))
            assert db.scalar(select(User).where(User.id == 'user-clinician').with_for_update(nowait=True))
            idle = db.execute(text("SELECT pid FROM pg_stat_activity WHERE datname=current_database() "
                                   "AND state='idle in transaction' AND pid<>pg_backend_pid()")).all()
            assert not idle, 'An application transaction remained open during inference'
        observations.append('independent_user_lock_and_no_idle_transaction')

    provider = FakeLiveProvider(callback=outside_transaction)
    install(monkeypatch, provider)
    with login() as client:
        document, task, payload = subject(client)
        operation = key()
        result = post(client, '/proposals', payload, operation_key=operation)
        replay = post(client, '/proposals', payload, operation_key=operation)
        assert replay == result and len(provider.calls) == 1
        assert provider.calls[0] == {'title': document['title'], 'content': CONTENT, 'checklist_id': CHECKLIST}
        assert result['demo'] is False and result['proposal']['demo'] is False
        assert result['run']['provider'] == 'dr_train_ollama'
        assert result['run']['outcome'] == 'success' and result['run']['measured_cost'] is None
        assert result['run']['usage']['prompt_eval_count'] == 101
        assert result['proposal']['evidence']['document_version_id'] == document['current_version_id']
        assert result['proposal']['action']['completeness'] == normalized_success()['action']['completeness']
        different_doc = post(client, '/documents', {
            'patient_id': 'patient-001', 'encounter_id': 'encounter-001',
            'title': 'Different synthetic source', 'content': CONTENT}, 201)
        post(client, '/proposals', {**payload, 'document_id': different_doc['id']},
             expected=409, operation_key=operation)
        assert len(provider.calls) == 1
        with SessionLocal() as db:
            runs = list(db.scalars(select(InferenceRun).where(InferenceRun.task_id == task['id'])))
            assert len(runs) == 1 and runs[0].operation_key == operation
            assert runs[0].completed_at is not None and runs[0].context_snapshot
            assert runs[0].provenance['model_digest'] == 'a' * 64
        TRACE.append({'check': 'live_content_unlocked_and_exact_replay', 'task_id': task['id'],
                      'document_id': document['id'], 'run_id': result['run']['id'],
                      'proposal_id': result['proposal']['id'], 'observations': observations})


def test_concurrent_same_key_returns_pending_and_calls_provider_once(monkeypatch):
    started, release = threading.Event(), threading.Event()

    def blocked():
        started.set()
        assert release.wait(20), 'Test did not release the synthetic provider'

    provider = FakeLiveProvider(callback=blocked)
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client)
        operation = key()

        def request():
            with cloned(client) as other:
                return post(other, '/proposals', payload, operation_key=operation)

        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(request)
            try:
                assert started.wait(10)
                pending = post(client, '/proposals', payload, expected=202, operation_key=operation)
                assert pending['proposal'] is None and pending['run']['outcome'] == 'running'
                assert len(provider.calls) == 1
            finally:
                release.set()
            result = first.result(timeout=10)
        assert result['proposal'] is not None
        assert post(client, '/proposals', payload, operation_key=operation) == result
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(InferenceRun).where(InferenceRun.task_id == task['id'])) == 1
            assert db.scalar(select(func.count()).select_from(Proposal).where(Proposal.task_id == task['id'])) == 1
        TRACE.append({'check': 'concurrent_same_key_single_inference', 'task_id': task['id'],
                      'run_id': result['run']['id'], 'operation_key': operation})


def test_global_live_admission_retains_busy_attempt_without_second_inference(monkeypatch):
    started, release = threading.Event(), threading.Event()

    def blocked():
        started.set()
        assert release.wait(20), 'Test did not release its admitted provider call'

    provider = FakeLiveProvider(callback=blocked)
    install(monkeypatch, provider)
    with login() as client, login('imaging') as busy_client:
        _, first_task, first_payload = subject(client)
        _, busy_task, busy_payload = subject(busy_client)
        busy_key = key()

        def request():
            with cloned(client) as other:
                return post(other, '/proposals', first_payload)

        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(request)
            try:
                assert started.wait(10)
                busy = post(busy_client, '/proposals', busy_payload, operation_key=busy_key)
                assert busy['proposal'] is None and busy['run']['outcome'] == 'failed'
                assert busy['run']['reason'] == 'LIVE_PROVIDER_BUSY'
                assert len(provider.calls) == 1
                no_proposal(busy_task['id'])
            finally:
                release.set()
            admitted = first.result(timeout=10)
        assert admitted['run']['outcome'] == 'success'
        # A retry of a rejected admission is the original result, even once the
        # slot is free. Starting a new inference requires an explicit new key.
        assert post(busy_client, '/proposals', busy_payload, operation_key=busy_key) == busy
        assert len(provider.calls) == 1 and busy['run']['measured_cost'] is None
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(InferenceRun).where(
                InferenceRun.task_id == busy_task['id'])) == 1
            assert db.get(InferenceRun, busy['run']['id']).actor_id == 'user-imaging'
        TRACE.append({'check': 'global_live_admission_busy_retained',
                      'admitted_task_id': first_task['id'], 'busy_task_id': busy_task['id'],
                      'busy_run_id': busy['run']['id'], 'busy_operation_key': busy_key,
                      'admitted_actor': 'user-clinician', 'busy_actor': 'user-imaging'})


def test_expired_running_lease_is_interrupted_and_late_completion_cannot_write(monkeypatch):
    started, release = threading.Event(), threading.Event()

    def blocked():
        started.set()
        assert release.wait(20), 'Test did not release its expired provider call'

    provider = FakeLiveProvider(callback=blocked)
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client)
        operation = key()

        def request():
            with cloned(client) as other:
                return post(other, '/proposals', payload, operation_key=operation)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(request)
            try:
                assert started.wait(10)
                # Advance the durable lease clock only in this isolated fixture;
                # no application state, approval or evidence is fabricated.
                with SessionLocal.begin() as db:
                    attempt = db.scalar(select(InferenceRun).where(
                        InferenceRun.task_id == task['id']).with_for_update())
                    attempt.created_at = utcnow()-timedelta(minutes=10)
                interrupted = post(client, '/proposals', payload, operation_key=operation)
                assert interrupted['proposal'] is None
                assert interrupted['run']['outcome'] == 'interrupted'
                assert interrupted['run']['reason'] == 'INFERENCE_LEASE_EXPIRED'
                assert len(provider.calls) == 1
            finally:
                release.set()
            late = pending.result(timeout=10)
        assert late == interrupted
        assert post(client, '/proposals', payload, operation_key=operation) == interrupted
        assert len(provider.calls) == 1
        no_proposal(task['id'])
        with SessionLocal() as db:
            attempts = list(db.scalars(select(InferenceRun).where(InferenceRun.task_id == task['id'])))
            assert len(attempts) == 1 and attempts[0].completed_at is not None
        TRACE.append({'check': 'expired_lease_and_late_result_fenced', 'task_id': task['id'],
                      'run_id': interrupted['run']['id'], 'operation_key': operation})


def test_live_settings_timeout_sets_full_lease_without_direct_provider_attribute(monkeypatch):
    delegate = FakeLiveProvider()
    # The actual adapter exposes timeout on its settings object; it must not be
    # assigned a shorter default lease than its authorized request deadline.
    provider = SimpleNamespace(is_live=True, demo=False, name=delegate.name,
                               model=delegate.model, model_digest=delegate.model_digest,
                               settings=SimpleNamespace(timeout_seconds=300),
                               public_config=delegate.public_config,
                               generate_document=delegate.generate_document)
    assert not hasattr(provider, 'timeout_seconds')
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client)
        result = post(client, '/proposals', payload)
        assert result['run']['outcome'] == 'success' and len(delegate.calls) == 1
        with SessionLocal() as db:
            run = db.get(InferenceRun, result['run']['id'])
            assert run.context_snapshot['lease_seconds'] == 360
        TRACE.append({'check': 'settings_timeout_lease_binding', 'task_id': task['id'],
                      'run_id': result['run']['id'], 'request_timeout_seconds': 300,
                      'durable_lease_seconds': 360})


def test_source_revision_changed_during_inference_is_retained_without_proposal(monkeypatch):
    started, release = threading.Event(), threading.Event()
    provider = FakeLiveProvider(callback=lambda: (started.set(), release.wait(20)))
    install(monkeypatch, provider)
    with login() as client:
        document, task, payload = subject(client)

        def request():
            with cloned(client) as other:
                return post(other, '/proposals', payload)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(request)
            try:
                assert started.wait(10)
                amended = post(client, '/documents/'+document['id']+'/revise', {
                    'version': document['version'], 'content': CONTENT+'\nฉบับแก้ไข',
                    'reason': 'Synthetic source changes during external inference'})
                assert amended['current_version_id'] != document['current_version_id']
            finally:
                release.set()
            result = pending.result(timeout=10)
        assert result['run']['outcome'] == 'stale_context' and result['proposal'] is None
        assert result['demo'] is False and len(provider.calls) == 1
        no_proposal(task['id'])
        with SessionLocal() as db:
            assert db.get(DocumentVersion, document['current_version_id']).content == CONTENT
            assert db.get(InferenceRun, result['run']['id']).outcome == 'stale_context'
        TRACE.append({'check': 'source_revision_fenced_after_inference', 'task_id': task['id'],
                      'run_id': result['run']['id'], 'original_revision_id': document['current_version_id']})


def test_session_revoked_during_inference_has_failed_attempt_and_no_write(monkeypatch):
    started, release = threading.Event(), threading.Event()
    provider = FakeLiveProvider(callback=lambda: (started.set(), release.wait(20)))
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client)
        cookie_hash = text_hash(client.cookies.get(COOKIE))

        def request():
            with cloned(client) as other:
                return other.post('/api/v2/proposals', json=payload,
                                  headers={'Idempotency-Key': key()})

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(request)
            try:
                assert started.wait(10)
                with SessionLocal.begin() as db:
                    session = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == cookie_hash))
                    session.revoked_at = utcnow()
            finally:
                release.set()
            denied = pending.result(timeout=10)
        assert denied.status_code in (401, 403), denied.text
        no_proposal(task['id'])
        with SessionLocal() as db:
            runs = list(db.scalars(select(InferenceRun).where(InferenceRun.task_id == task['id'])))
            assert len(runs) == 1 and runs[0].outcome == 'permission_revoked'
            assert runs[0].completed_at is not None
        TRACE.append({'check': 'revoked_session_fenced_after_inference', 'task_id': task['id'],
                      'run_id': runs[0].id, 'response_status': denied.status_code})


@pytest.mark.parametrize('changed', ['task_version', 'encounter_version', 'task_domain'])
def test_current_task_and_encounter_versions_are_rechecked_after_inference(monkeypatch, changed):
    started, release = threading.Event(), threading.Event()
    provider = FakeLiveProvider(callback=lambda: (started.set(), release.wait(20)))
    install(monkeypatch, provider)
    with login() as client:
        encounter = post(client, '/encounters', {'patient_id': 'patient-001', 'kind': 'OPD'}, 201)
        _, task, payload = subject(client, encounter_id=encounter['id'])

        def request():
            with cloned(client) as other:
                return post(other, '/proposals', payload)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(request)
            try:
                assert started.wait(10)
                if changed == 'task_version':
                    post(client, '/tasks/'+task['id']+'/transition', {
                        'version': task['version'], 'target': 'in_progress'})
                elif changed == 'task_domain':
                    # Emulate an integration/operator reassignment without a
                    # version bump: current domain is independently rechecked.
                    with SessionLocal.begin() as db:
                        db.get(Task, task['id']).domain = 'D10'
                else:
                    post(client, '/encounters/'+encounter['id']+'/transition', {
                        'version': encounter['version'], 'target': 'in_consult'})
            finally:
                release.set()
            result = pending.result(timeout=10)
        assert result['run']['outcome'] == 'stale_context' and result['proposal'] is None
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(Proposal).where(Proposal.task_id == task['id'])) == 0
            assert db.scalar(select(func.count()).select_from(CommittedResult).where(CommittedResult.task_id == task['id'])) == 0
        TRACE.append({'check': 'current_version_fence_'+changed, 'task_id': task['id'],
                      'encounter_id': encounter['id'], 'run_id': result['run']['id']})


@pytest.mark.parametrize('outcome', ['failed', 'timeout', 'invalid_output', 'abstained'])
def test_live_failed_attempts_are_retained_and_replayed_without_fallback(monkeypatch, outcome):
    response = {**normalized_success(), 'outcome': outcome, 'action': None,
                'reason': 'SYNTHETIC_PROVIDER_'+outcome.upper()}
    provider = FakeLiveProvider(outcome=response)
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client)
        operation = key()
        result = post(client, '/proposals', payload, operation_key=operation)
        assert result['proposal'] is None and result['run']['outcome'] == outcome
        assert result['demo'] is False and result['run']['provider'] == 'dr_train_ollama'
        assert post(client, '/proposals', payload, operation_key=operation) == result
        assert len(provider.calls) == 1
        no_proposal(task['id'])
        with SessionLocal() as db:
            runs = list(db.scalars(select(InferenceRun).where(InferenceRun.task_id == task['id'])))
            assert len(runs) == 1 and runs[0].outcome == outcome and runs[0].measured_cost is None
            audits = list(db.scalars(select(AuditEvent).where(
                AuditEvent.entity_id == runs[0].id, AuditEvent.domain == 'D37')))
            assert len(audits) == 2 and all(a.actor_id == 'user-clinician' for a in audits)
            assert sum(a.action == 'inference_started' for a in audits) == 1
            assert sum(a.action == 'inference_'+outcome for a in audits) == 1
        TRACE.append({'check': 'failed_attempt_retained_'+outcome, 'task_id': task['id'],
                      'run_id': result['run']['id'], 'operation_key': operation})


def test_reviewer_edit_preserves_report_and_requires_new_bound_approval(monkeypatch):
    provider = FakeLiveProvider()
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client)
        created = post(client, '/proposals', payload)
        proposal = created['proposal']
        original = deepcopy(proposal)
        approved = post(client, '/proposals/'+proposal['id']+'/review', {
            'version': proposal['version'], 'action_hash': proposal['action_hash'], 'decision': 'approve'})
        edited = post(client, '/proposals/'+proposal['id']+'/review', {
            'version': approved['version'], 'action_hash': approved['action_hash'],
            'decision': 'edit', 'edited_text': 'ผู้ตรวจแก้คำอธิบายโดยอ้างหลักฐานเดิม'})
        assert edited['status'] == 'pending' and edited['version'] == original['version']+1
        assert edited['action_hash'] != original['action_hash']
        assert edited['action']['completeness'] == original['action']['completeness']
        post(client, '/proposals/'+proposal['id']+'/commit', {
            'version': approved['version'], 'action_hash': approved['action_hash']}, expected=409)
        edited = post(client, '/proposals/'+proposal['id']+'/review', {
            'version': edited['version'], 'action_hash': edited['action_hash'], 'decision': 'approve'})
        result = post(client, '/proposals/'+proposal['id']+'/commit', {
            'version': edited['version'], 'action_hash': edited['action_hash']})
        assert result['action']['completeness'] == original['action']['completeness']
        with SessionLocal() as db:
            versions = list(db.scalars(select(ProposalVersion).where(
                ProposalVersion.proposal_id == proposal['id']).order_by(ProposalVersion.version)))
            assert len(versions) == 2
            assert json.loads(versions[0].action_canonical) == original['action']
            assert json.loads(versions[1].action_canonical) == edited['action']
        TRACE.append({'check': 'report_and_human_edit_binding', 'task_id': task['id'],
                      'proposal_id': proposal['id'], 'result_id': result['id']})


@pytest.mark.parametrize('kind,scenario', [('dr_review', 'success'), ('document_review', 'failure')])
def test_live_unsupported_kind_or_mock_scenario_never_calls_provider(monkeypatch, kind, scenario):
    provider = FakeLiveProvider()
    install(monkeypatch, provider)
    with login() as client:
        _, task, payload = subject(client, kind)
        post(client, '/proposals', {**payload, 'scenario': scenario}, expected=422)
        assert not provider.calls
        no_proposal(task['id'])
        TRACE.append({'check': 'unsupported_live_request_no_inference', 'task_id': task['id'],
                      'kind': kind, 'scenario': scenario, 'response_status': 422})
