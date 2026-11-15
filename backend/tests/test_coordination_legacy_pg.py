"""Operational ownership must not invalidate immutable legacy evidence or exchanges.

Actual disposable PostgreSQL18 and application HTTP transactions. Provider and
connector transports are explicit offline doubles; no real model/socket calls.
"""
import os
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

assert os.getenv('HIS_TEST_DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL') == os.getenv('DATABASE_URL'), 'Disposable PostgreSQL wrapper required'

from backend.app import dr_gateway, providers
from backend.app.common import canonical, digest, uid, utcnow
from backend.app.db import SessionLocal, engine
from backend.app.models import CareAssignment, CommittedResult, DocumentVersion, InferenceRun, Proposal, ProposalVersion, Task, TaskCoordination
from backend.app.models_clinical import LabRequest
from backend.app.models_dr import DRAttempt, DRBinding, DRExchange
from backend.app.models_integrations import ConnectorAttempt, ConnectorBinding, ConnectorExchange
from backend.app.seed import seed
from backend.app.task_identity import task_source_version
from backend.tests.test_assistant_pg import context
from backend.tests import test_dr_gateway_pg as dr_fixtures
from backend.tests import test_labclear_gateway_pg as lab_fixtures


@pytest.fixture(scope='module', autouse=True)
def isolated_database():
    assert engine.url.database == 'his_test' and engine.url.host == '127.0.0.1'
    with SessionLocal.begin() as db:
        seed(db, os.environ['HIS_SEED_PASSWORD'])


def post(client, path, body, *, status=200, key=None):
    response = client.post('/api/v2' + path, json=body, headers={'Idempotency-Key': key or uid()})
    assert response.status_code == status, (path, response.status_code, response.text)
    return response.json()


def legacy_context():
    with SessionLocal.begin() as db:
        patient, encounter, document = context(db, lab=False)
        task = Task(id=uid(), organization_id='org-demo', facility_id='facility-demo', patient_id=patient,
                    encounter_id=encounter, domain='D37', kind='document_review', title='Authored coordination regression', status='open')
        db.add(task); db.flush()
        return patient, encounter, document, task.id


def read_task(client, identity):
    response = client.get('/api/v2/team-queue/tasks/' + identity)
    assert response.status_code == 200, response.text
    return response.json()


def coordinate(client, identity):
    """Exercise real claim, overdue scheduling and escalation transactions."""
    initial = read_task(client, identity)
    claimed = post(client, '/team-queue/tasks/' + identity + '/claim', {'version': initial['version']})
    scheduled = post(client, '/team-queue/tasks/' + identity + '/schedule', {
        'version': claimed['version'], 'due_at': (utcnow() - timedelta(minutes=5)).isoformat(), 'priority': 'high'})
    escalated = post(client, '/team-queue/tasks/' + identity + '/escalate', {
        'version': scheduled['version'], 'reason': 'Authored overdue work follow-up'})
    assert escalated['assignee']['id'] == 'user-clinician' and escalated['escalation_level'] == 1
    assert escalated['version'] == initial['version'] + 3
    with SessionLocal() as db:
        task = db.get(Task, identity)
        assert task_source_version(db, task) == 1
        assert db.get(TaskCoordination, identity).operational_updates == 3
    return escalated


def immutable_proposal(identity):
    with SessionLocal() as db:
        proposal = db.get(Proposal, identity)
        version = db.scalar(select(ProposalVersion).where(ProposalVersion.proposal_id == identity, ProposalVersion.version == 1))
        source = db.get(DocumentVersion, proposal.document_version_id)
        return canonical({'task_version': proposal.task_version, 'document_version_id': proposal.document_version_id,
            'encounter_version': proposal.encounter_version, 'action': proposal.action_canonical,
            'hash': proposal.action_hash, 'version_action': version.action_canonical, 'version_hash': version.action_hash,
            'source_content': source.content, 'source_hash': source.content_hash})


@pytest.mark.parametrize('coordinate_first', [False, True])
def test_mock_proposal_semantic_identity_survives_coordination_and_commit_exactly_once(monkeypatch, coordinate_first):
    monkeypatch.setenv('HIS_AI_PROVIDER', 'mock_demo')
    _, _, document, identity = legacy_context()
    with lab_fixtures.logged_in() as client:
        if coordinate_first:
            coordinate(client, identity)
        proposal = post(client, '/proposals', {'task_id': identity, 'document_id': document})['proposal']
        assert proposal['evidence']['task_version'] == 1
        original = immutable_proposal(proposal['id'])
        if not coordinate_first:
            coordinate(client, identity)
        approved = post(client, '/proposals/' + proposal['id'] + '/review', {
            'version': proposal['version'], 'action_hash': proposal['action_hash'], 'decision': 'approve'})
        payload = {'version': approved['version'], 'action_hash': approved['action_hash']}
        key = uid()
        result = post(client, '/proposals/' + proposal['id'] + '/commit', payload, key=key)
        assert post(client, '/proposals/' + proposal['id'] + '/commit', payload, key=key) == result
        assert immutable_proposal(proposal['id']) == original
    with SessionLocal() as db:
        task = db.get(Task, identity)
        assert (task.version, task.status, task.assignee_id) == (5, 'completed', 'user-clinician')
        assert task_source_version(db, task) == 2  # Completion remains a genuine semantic change.
        assert db.scalar(select(func.count()).select_from(CommittedResult).where(CommittedResult.proposal_id == proposal['id'])) == 1


class OfflineLiveProvider:
    """Runs the real two-phase live path with one synchronous offline callback."""
    name = 'offline_coordination_live_double'
    is_live = True
    timeout_seconds = 5

    def __init__(self, callback):
        self.callback, self.calls = callback, 0

    def public_config(self):
        return {'route': 'offline-coordination-test', 'model_digest': 'authored-double-only'}

    def generate_document(self, title, content, checklist):
        assert engine.pool.checkedout() == 0, 'Legacy live path retained a database connection'
        self.calls += 1
        assert self.calls == 1
        self.callback()
        return {'outcome': 'success', 'reason': None, 'elapsed_ms': 1, 'usage': {'eval_count': 7},
            'provenance': {'offline_test_double': True}, 'action': {'text': 'Authored draft requiring human review',
            'completeness': {'checklist_id': checklist, 'items': [], 'summary': 'Authored fixture', 'requires_human_review': True}}}


def test_live_proposal_coordination_during_inference_finalizes_original_semantic_snapshot_once(monkeypatch):
    _, _, document, identity = legacy_context()
    with lab_fixtures.logged_in() as coordinator, lab_fixtures.logged_in() as client:
        provider = OfflineLiveProvider(lambda: coordinate(coordinator, identity))
        monkeypatch.setattr(providers, 'resolve_provider', lambda: provider)
        key = uid(); body = {'task_id': identity, 'document_id': document}
        response = post(client, '/proposals', body, key=key)
        assert response['run']['outcome'] == 'success'
        assert response['proposal']['evidence']['task_version'] == 1
        assert post(client, '/proposals', body, key=key) == response
        assert provider.calls == 1
    with SessionLocal() as db:
        run = db.get(InferenceRun, response['run']['id'])
        assert run.context_snapshot['task_version'] == 1
        assert db.get(Task, identity).version == 4
        assert db.scalar(select(func.count()).select_from(InferenceRun).where(InferenceRun.task_id == identity)) == 1
        assert db.scalar(select(func.count()).select_from(Proposal).where(Proposal.task_id == identity)) == 1


def semantic_change(client, kind, patient, document, identity):
    if kind == 'task_status':
        task = read_task(client, identity)
        post(client, '/tasks/' + identity + '/transition', {'version': task['version'], 'target': 'in_progress'})
    elif kind == 'document_revision':
        response = client.get('/api/v2/documents/' + document)
        assert response.status_code == 200
        post(client, '/documents/' + document + '/revise', {'version': response.json()['version'],
            'content': 'New authored source after evidence capture', 'reason': 'Synthetic semantic-change guard'})
    else:
        with SessionLocal.begin() as db:
            db.get(CareAssignment, ('user-clinician', patient)).active = False


@pytest.mark.parametrize('change,status', [('task_status', 409), ('document_revision', 409), ('care_permission', 404)])
@pytest.mark.parametrize('phase', ['review', 'commit'])
def test_existing_mock_proposal_still_rejects_real_source_status_or_permission_changes(monkeypatch, change, status, phase):
    monkeypatch.setenv('HIS_AI_PROVIDER', 'mock_demo')
    patient, _, document, identity = legacy_context()
    with lab_fixtures.logged_in() as client:
        proposal = post(client, '/proposals', {'task_id': identity, 'document_id': document})['proposal']
        original = immutable_proposal(proposal['id'])
        if phase == 'commit':
            proposal = post(client, '/proposals/' + proposal['id'] + '/review', {'version': proposal['version'],
                'action_hash': proposal['action_hash'], 'decision': 'approve'})
        coordinate(client, identity)
        semantic_change(client, change, patient, document, identity)
        payload = {'version': proposal['version'], 'action_hash': proposal['action_hash']}
        if phase == 'review':
            payload['decision'] = 'approve'
        post(client, '/proposals/' + proposal['id'] + '/' + phase, payload, status=status)
        assert immutable_proposal(proposal['id']) == original
    with SessionLocal() as db:
        assert db.get(Proposal, proposal['id']).status == ('pending' if phase == 'review' else 'approved')
        assert db.scalar(select(func.count()).select_from(CommittedResult).where(CommittedResult.proposal_id == proposal['id'])) == 0


@pytest.mark.parametrize('change,status', [('task_status', 200), ('document_revision', 200), ('care_permission', 404)])
def test_live_finalization_still_fences_actual_source_status_or_permission_change(monkeypatch, change, status):
    patient, _, document, identity = legacy_context()
    with lab_fixtures.logged_in() as coordinator, lab_fixtures.logged_in() as client:
        def callback():
            coordinate(coordinator, identity)
            semantic_change(coordinator, change, patient, document, identity)
        provider = OfflineLiveProvider(callback)
        monkeypatch.setattr(providers, 'resolve_provider', lambda: provider)
        response = post(client, '/proposals', {'task_id': identity, 'document_id': document}, status=status)
        if status == 200:
            assert response['proposal'] is None and response['run']['outcome'] == 'stale_context'
        assert provider.calls == 1
    with SessionLocal() as db:
        run = db.scalar(select(InferenceRun).where(InferenceRun.task_id == identity))
        assert run.outcome == ('permission_revoked' if change == 'care_permission' else 'stale_context')
        assert run.context_snapshot['task_version'] == 1
        assert db.scalar(select(func.count()).select_from(Proposal).where(Proposal.task_id == identity)) == 0


@pytest.fixture
def lab_receiver():
    yield from lab_fixtures.receiver.__wrapped__()


@pytest.mark.parametrize('operation', ['import', 'confirm'])
def test_labclear_write_exchange_survives_midflight_coordination_once(lab_receiver, operation):
    body, key = lab_fixtures.source_fixture(), uid()
    with lab_fixtures.logged_in() as client, lab_fixtures.logged_in() as coordinator:
        if operation == 'confirm':
            imported, _ = lab_fixtures.imported(client, body)
            path = lab_fixtures.BASE + '/bindings/' + imported['binding']['id'] + '/confirm'
            payload = lab_fixtures.confirm_body(imported)
        else:
            path, payload = lab_fixtures.BASE + '/import', body
        original_calls = len(lab_receiver.calls)
        lab_receiver.hook = lambda _: coordinate(coordinator, body['task_id'])
        first = client.post(path, json=payload, headers={'Idempotency-Key': key})
        assert first.status_code == 200, first.text
        repeated = client.post(path, json=payload, headers={'Idempotency-Key': key})
        assert repeated.status_code == 200 and repeated.json() == first.json()
        assert len(lab_receiver.calls) == original_calls + 1
    with SessionLocal() as db:
        attempt = db.scalar(select(ConnectorAttempt).where(ConnectorAttempt.operation_key == key))
        exchange = db.scalar(select(ConnectorExchange).where(ConnectorExchange.attempt_id == attempt.id))
        assert attempt.status == exchange.outcome == 'succeeded' and not exchange.quarantined
        assert exchange.context_snapshot['task_version'] == 1
        assert db.get(ConnectorBinding, attempt.binding_id).state == ('confirmed' if operation == 'confirm' else 'draft')
        assert db.scalar(select(func.count()).select_from(ConnectorExchange).where(ConnectorExchange.attempt_id == attempt.id)) == 1
        source, task = db.get(LabRequest, body['source_id']), db.get(Task, body['task_id'])
        assert (source.result_value, source.version, task.status, task.version) == ('42', 5, 'open', 4)


@pytest.fixture
def dr_receiver(monkeypatch, tmp_path):
    import json
    client, body = dr_fixtures.login(), dr_fixtures.fixture_sources(1)
    created = client.post(dr_fixtures.BASE + '/source-sets', json=body, headers={'Idempotency-Key': uid()})
    assert created.status_code == 200, created.text
    source_set = created.json(); scope = source_set['scope']
    registry = tmp_path / 'coordination-dr-destinations.json'
    registry.write_text(json.dumps({'version': 1, 'destinations': [{'id': 'fixture', 'origin': 'http://127.0.0.1:19899',
        'key': dr_fixtures.KEY.decode(), 'scope': scope, 'workspace_id': 'cb-' + digest(scope)[:32]}]}))
    registry.chmod(0o600)
    monkeypatch.setenv('HIS_DR_ENABLED', 'true')
    monkeypatch.setenv('HIS_DR_DESTINATIONS_FILE', str(registry))
    receiver, original = dr_fixtures.Receiver(), dr_gateway.DRClient
    monkeypatch.setattr(dr_gateway, 'DRClient', lambda destination, **kwargs: original(destination, httpx.MockTransport(receiver), **kwargs))
    try:
        yield client, body, source_set, receiver
    finally:
        client.close()


@pytest.mark.parametrize('operation', ['import', 'dispatch'])
def test_dr_write_exchange_survives_midflight_coordination_once(dr_receiver, operation):
    client, body, source_set, receiver = dr_receiver
    import_path = dr_fixtures.BASE + '/source-sets/' + source_set['id'] + '/bindings'
    consent = {'transfer_consent': body['transfer_consent']}
    if operation == 'dispatch':
        imported = client.post(import_path, json=consent, headers={'Idempotency-Key': uid()})
        assert imported.status_code == 200, imported.text
        binding = imported.json()['binding_id']
        image = source_set['sources'][0]['image_sha256']
        path = '/integrations/dr/' + binding + '/api/v1/cases/' + image + '/admission'
        payload = {'revision': 0, 'action': 'QUALITY_ACCEPTABLE'}
    else:
        path, payload = import_path, consent
    key, original_calls = uid(), len(receiver.calls)
    with dr_fixtures.login() as coordinator:
        receiver.hook = lambda _: coordinate(coordinator, body['task_id'])
        first = client.post(path, json=payload, headers={'Idempotency-Key': key})
        assert first.status_code == 200, first.text
        repeated = client.post(path, json=payload, headers={'Idempotency-Key': key})
        assert repeated.status_code == 200 and repeated.json() == first.json()
        assert len(receiver.calls) == original_calls + 1
    with SessionLocal() as db:
        attempt = db.scalar(select(DRAttempt).where(DRAttempt.operation_key == key))
        exchange = db.scalar(select(DRExchange).where(DRExchange.attempt_id == attempt.id))
        assert attempt.status == exchange.outcome == 'succeeded' and not exchange.quarantined
        assert exchange.context_snapshot['task_version'] == 1
        assert db.get(DRBinding, attempt.binding_id).state == 'imported'
        assert db.scalar(select(func.count()).select_from(DRExchange).where(DRExchange.attempt_id == attempt.id)) == 1
        assert (db.get(Task, body['task_id']).status, db.get(Task, body['task_id']).version) == ('open', 4)


def test_coordination_mutations_still_require_physical_queue_version():
    _, _, _, identity = legacy_context()
    with lab_fixtures.logged_in() as client:
        claimed = post(client, '/team-queue/tasks/' + identity + '/claim', {'version': 1})
        assert claimed['version'] == 2
        post(client, '/team-queue/tasks/' + identity + '/schedule', {'version': 1, 'due_at': None, 'priority': 'high'}, status=409)
        scheduled = post(client, '/team-queue/tasks/' + identity + '/schedule', {
            'version': 2, 'due_at': (utcnow() - timedelta(minutes=1)).isoformat(), 'priority': 'high'})
        assert scheduled['version'] == 3
        post(client, '/team-queue/tasks/' + identity + '/escalate', {'version': 2, 'reason': 'Stale physical version'}, status=409)
    with SessionLocal() as db:
        task, coordination = db.get(Task, identity), db.get(TaskCoordination, identity)
        assert (task.version, coordination.operational_updates, coordination.escalation_level) == (3, 2, 0)
        assert task_source_version(db, task) == 1
