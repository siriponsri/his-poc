"""Regression coverage for direct service calls and the bounded demo workflow."""
import concurrent.futures
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.his_poc.service import DomainError, Service


class ServiceRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Service(Path(self.tmp.name) / 'service.db')
        self.actor = 'reviewer-demo'

    def tearDown(self):
        self.tmp.cleanup()

    def proposal(self, service=None):
        return (service or self.s).propose(self.actor, 'p-demo', 'e-demo')['proposal']

    def approve(self, proposal, service=None):
        return (service or self.s).review(
            self.actor, proposal['id'], proposal['version'], proposal['action_hash'], 'approve')

    def commit(self, proposal, service=None):
        return (service or self.s).commit(
            self.actor, proposal['id'], proposal['version'], proposal['action_hash'], 'regression-key-01')

    def fails(self, code, operation, status=409):
        with self.assertRaises(DomainError) as raised:
            operation()
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(raised.exception.status, status)

    def test_approve_and_reject_with_edits_fail_without_mutation(self):
        proposal = self.proposal()
        before = self.s.context(self.actor)
        for decision in ('approve', 'reject'):
            for edits in ('', 'Changed text', {}, [], True, 0):
                with self.subTest(decision=decision, edits=edits):
                    self.fails('INVALID_EDITS', lambda: self.s.review(
                        self.actor, proposal['id'], 1, proposal['action_hash'], decision, edits), 400)
                    self.assertEqual(self.s.context(self.actor), before)

    def test_review_requires_positive_integer_version_excluding_boolean(self):
        proposal = self.proposal()
        before = self.s.context(self.actor)
        for version in (True, False, 1.0, '1', 0, -1, None):
            with self.subTest(version=version):
                self.fails('INVALID_VERSION', lambda: self.s.review(
                    self.actor, proposal['id'], version, proposal['action_hash'], 'approve'), 400)
                self.assertEqual(self.s.context(self.actor), before)

    def test_commit_requires_positive_integer_version_excluding_boolean(self):
        proposal = self.proposal()
        self.approve(proposal)
        before = self.s.context(self.actor)
        for version in (True, False, 1.0, '1', 0, -1, None):
            with self.subTest(version=version):
                self.fails('INVALID_VERSION', lambda: self.s.commit(
                    self.actor, proposal['id'], version, proposal['action_hash'], 'regression-key-01'), 400)
                self.assertEqual(self.s.context(self.actor), before)
                with self.s.db() as c:
                    self.assertEqual(c.execute('SELECT count(*) FROM idempotency').fetchone()[0], 0)

    def test_document_update_requires_positive_integer_version_excluding_boolean(self):
        before = self.s.context(self.actor)
        for version in (True, False, 1.0, '1', 0, -1, None):
            with self.subTest(version=version):
                self.fails('INVALID_VERSION', lambda: self.s.update_document(
                    self.actor, 'p-demo', 'e-demo', version, {'text': 'Changed'}), 400)
                self.assertEqual(self.s.context(self.actor), before)

    def test_invalid_document_content_is_not_persisted(self):
        before = self.s.context(self.actor)
        invalid_contents = (
            None, [], {}, {'text': None}, {'text': True},
            {'text': 'Changed', 'author': {'not': 'a string'}},
            {'text': 'Changed', 'signed_at': 1},
            {'text': 'Changed', 'unexpected': 'ignored'},
        )
        for content in invalid_contents:
            with self.subTest(content=content):
                self.fails('INVALID_DOCUMENT', lambda: self.s.update_document(
                    self.actor, 'p-demo', 'e-demo', 1, content), 400)
                self.assertEqual(self.s.context(self.actor), before)

    def test_commit_completes_only_named_demo_task_and_retry_remains_safe(self):
        with self.s.db() as c:
            c.executemany('INSERT INTO tasks VALUES(?,?,?)', (
                ('unrelated-follow-up', 'e-demo', 'open'),
                ('unrelated-cancelled', 'e-demo', 'cancelled'),
            ))
        proposal = self.proposal()
        self.approve(proposal)
        first = self.commit(proposal)
        replay = self.commit(proposal)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        context = self.s.context(self.actor)
        tasks = {task['id']: task['status'] for task in context['tasks']}
        self.assertEqual(tasks, {
            'task-demo': 'completed', 'unrelated-follow-up': 'open',
            'unrelated-cancelled': 'cancelled',
        })
        self.assertEqual(len(context['results']), 1)
        self.assertEqual(sum(a['event'] == 'result_committed' for a in context['audit']), 1)

    def test_unavailable_or_mismatched_target_prevents_commit_atomically(self):
        cases = (
            ("DELETE FROM tasks WHERE id='task-demo'", 'TASK_NOT_FOUND'),
            ("UPDATE tasks SET status='cancelled' WHERE id='task-demo'", 'TASK_NOT_OPEN'),
            ("UPDATE tasks SET status='completed' WHERE id='task-demo'", 'TASK_NOT_OPEN'),
            ("UPDATE tasks SET encounter='e-other' WHERE id='task-demo'", 'TASK_CONTEXT_MISMATCH'),
        )
        for index, (sql, code) in enumerate(cases):
            with self.subTest(code=code, sql=sql):
                service = Service(Path(self.tmp.name) / ('case-' + str(index) + '.db'))
                proposal = self.proposal(service)
                self.approve(proposal, service)
                with service.db() as c:
                    c.execute(sql)
                before = service.context(self.actor)
                self.fails(code, lambda: self.commit(proposal, service))
                self.assertEqual(service.context(self.actor), before)
                self.assertEqual(before['proposals'][0]['status'], 'approved')
                with service.db() as c:
                    self.assertEqual(c.execute('SELECT count(*) FROM idempotency').fetchone()[0], 0)

    def test_closed_target_rejects_proposal_and_review_without_side_effects(self):
        proposal = self.proposal()
        with self.s.db() as c:
            c.execute("UPDATE tasks SET status='cancelled' WHERE id='task-demo'")
        before = self.s.context(self.actor)
        with patch('src.his_poc.service.resolve_provider') as resolver:
            self.fails('TASK_NOT_OPEN', lambda: self.proposal())
            resolver.assert_not_called()
        self.fails('TASK_NOT_OPEN', lambda: self.approve(proposal))
        self.assertEqual(self.s.context(self.actor), before)

    def test_target_closed_during_inference_retains_failed_attempt(self):
        def generate(_):
            with self.s.db() as c:
                c.execute("UPDATE tasks SET status='cancelled' WHERE id='task-demo'")
            return {'outcome': 'success', 'action': {
                'kind': 'document_completeness', 'summary': 'Demo', 'missing_fields': []}}
        with patch('src.his_poc.service.resolve_provider') as resolver:
            resolver.return_value.name = 'test'
            resolver.return_value.revision = 'test'
            resolver.return_value.generate.side_effect = generate
            response = self.s.propose(self.actor, 'p-demo', 'e-demo')
        self.assertEqual(response['outcome'], 'failed')
        self.assertEqual(response['error'], 'TASK_NOT_OPEN')
        context = self.s.context(self.actor)
        self.assertEqual(context['proposals'], [])
        self.assertEqual(len(context['runs']), 1)
        self.assertEqual(context['runs'][0]['error'], 'TASK_NOT_OPEN')
        self.assertEqual(sum(a['event'] == 'ai_run' for a in context['audit']), 1)

    def test_restart_does_not_recreate_a_missing_target(self):
        with self.s.db() as c:
            c.execute("DELETE FROM tasks WHERE id='task-demo'")
        restarted = Service(self.s.path)
        self.fails('TASK_NOT_FOUND', lambda: self.proposal(restarted))
        self.assertEqual(restarted.context(self.actor)['tasks'], [])

    def test_other_encounter_requires_an_explicit_future_task_binding(self):
        with self.s.db() as c:
            c.execute('INSERT INTO encounters VALUES(?,?,?,?)', ('e-other', 'p-demo', 1, 'open'))
            c.execute('INSERT INTO documents VALUES(?,?,?,?)', ('d-other', 'e-other', 1, '{"text":"Demo"}'))
            c.execute('INSERT INTO tasks VALUES(?,?,?)', ('other-task', 'e-other', 'open'))
        self.fails('UNSUPPORTED_TASK_SCOPE', lambda: self.s.propose(self.actor, 'p-demo', 'e-other'))
        context = self.s.context(self.actor, 'p-demo', 'e-other')
        self.assertEqual(context['proposals'], [])
        self.assertEqual(context['runs'], [])
        self.assertEqual(context['tasks'][0]['status'], 'open')

    def test_abstention_reason_survives_reload_and_is_bounded(self):
        short = self.s.propose(self.actor, 'p-demo', 'e-demo', 'abstain')
        reason = '\u0e01' * 1100
        with patch('src.his_poc.service.resolve_provider') as resolver:
            resolver.return_value.name = 'test'
            resolver.return_value.revision = 'test'
            resolver.return_value.generate.return_value = {
                'outcome': 'abstained', 'reason': reason, 'raw_payload': 'do not retain this payload'}
            bounded = self.s.propose(self.actor, 'p-demo', 'e-demo')
        self.assertEqual(bounded['reason'], reason[:1000])
        context = Service(self.s.path).context(self.actor)
        runs = {run['id']: run for run in context['runs']}
        self.assertEqual(runs[short['run_id']]['abstain_reason'], short['reason'])
        self.assertEqual(runs[bounded['run_id']]['abstain_reason'], bounded['reason'])
        details = {json.loads(a['details'])['run_id']: json.loads(a['details'])
                   for a in context['audit'] if a['event'] == 'ai_run'}
        self.assertEqual(details[bounded['run_id']]['abstain_reason'], bounded['reason'])
        self.assertNotIn('do not retain this payload', json.dumps(context))
        self.assertEqual(context['proposals'], [])

    def test_old_run_table_is_migrated_once_without_inventing_reason_or_reopening_task(self):
        path = Path(self.tmp.name) / 'legacy.db'
        with sqlite3.connect(path) as c:
            c.execute('CREATE TABLE runs(id TEXT PRIMARY KEY, encounter TEXT, outcome TEXT, '
                      'provider TEXT, model_revision TEXT, latency_ms REAL, usage TEXT, '
                      'cost REAL, error TEXT, demo INTEGER)')
            old_run = ('legacy-run', 'e-demo', 'abstained', 'mock', 'synthetic_fixture_v1',
                       1.0, 'null', None, None, 1)
            c.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)', old_run)
            c.execute('CREATE TABLE tasks(id TEXT PRIMARY KEY, encounter TEXT, status TEXT)')
            c.execute('INSERT INTO tasks VALUES(?,?,?)', ('task-demo', 'e-demo', 'cancelled'))
        # Simultaneous initializers must serialize the additive migration.
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: Service(path), range(2)))
        service = Service(path)
        context = service.context(self.actor)
        self.assertIsNone(context['runs'][0]['abstain_reason'])
        self.assertEqual(context['tasks'][0]['status'], 'cancelled')
        with service.db() as c:
            columns = [row['name'] for row in c.execute('PRAGMA table_info(runs)')]
            self.assertEqual(columns.count('abstain_reason'), 1)
            self.assertEqual(tuple(c.execute('SELECT * FROM runs').fetchone())[:-1], old_run)
            c.execute("UPDATE tasks SET status='open' WHERE id='task-demo'")
        response = service.propose(self.actor, 'p-demo', 'e-demo', 'abstain')
        current_runs = service.context(self.actor)['runs']
        self.assertEqual(len(current_runs), 2)
        current = next(run for run in current_runs if run['id'] == response['run_id'])
        self.assertEqual(current['abstain_reason'], response['reason'])


if __name__ == '__main__':
    unittest.main()
