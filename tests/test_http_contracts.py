"""HTTP boundary regressions. These tests require only the Python stdlib."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from src.his_poc.server import make_server
from src.his_poc.service import Service


class HTTPContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = Service(Path(self.tmp.name) / 'http.sqlite3')
        self.server = make_server(self.service, 0)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, body=None, *, raw=None, token='demo-reviewer-token', headers=None):
        request_headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
        request_headers.update(headers or {})
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers)
        try:
            response = urllib.request.urlopen(request, timeout=7)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    def proposal(self):
        status, body = self.request('/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'})
        self.assertEqual(status, 200)
        return body['proposal']

    def binding(self, proposal):
        return {'proposal_id': proposal['id'], 'version': proposal['version'], 'action_hash': proposal['action_hash']}

    def assert_invalid_without_writes(self, path, body=None, **kwargs):
        before = self.service.context('reviewer-demo')
        status, response = self.request(path, body, **kwargs)
        self.assertEqual(status, 400, response)
        self.assertIn('error', response)
        self.assertEqual(self.service.context('reviewer-demo'), before)

    def test_invalid_scope_fields_and_extra_fields_do_not_create_runs(self):
        for body in [
            {'patient': [], 'encounter': 'e-demo'},
            {'patient': 'p-demo', 'encounter': {}},
            {'patient': '', 'encounter': 'e-demo'},
            {'patient': 'p-demo'},
            {'patient': 'p-demo', 'encounter': 'e-demo', 'unexpected': 'ignored'},
            {'patient': 'p-demo', 'encounter': 'e-demo', 'data_class': 'restricted'},
            {'patient': 'p-demo', 'encounter': 'e-demo', 'scenario': ['success']},
        ]:
            with self.subTest(body=body):
                self.assert_invalid_without_writes('/api/v1/proposals', body)

    def test_boolean_and_malformed_versions_are_rejected_before_mutation(self):
        binding = self.binding(self.proposal())
        for value in (True, False, None, '1', 0, -1, 1.5, [], {}):
            for path, body in (
                ('/api/v1/reviews', {**binding, 'version': value, 'decision': 'approve'}),
                ('/api/v1/commits', {**binding, 'version': value, 'idempotency_key': 'invalid-version-key'}),
                ('/api/v1/documents', {'patient': 'p-demo', 'encounter': 'e-demo', 'expected_version': value, 'content': {'text': 'changed'}}),
            ):
                with self.subTest(path=path, value=value):
                    self.assert_invalid_without_writes(path, body)

    def test_approve_and_reject_forbid_edits_even_null(self):
        binding = self.binding(self.proposal())
        for decision in ('approve', 'reject'):
            for edits in (None, '', 'new text', {}, []):
                with self.subTest(decision=decision, edits=edits):
                    self.assert_invalid_without_writes('/api/v1/reviews', {**binding, 'decision': decision, 'edits': edits})

    def test_edit_requires_nonblank_bounded_text_and_valid_binding(self):
        binding = self.binding(self.proposal())
        for body in [
            {**binding, 'decision': 'edit'},
            *[{**binding, 'decision': 'edit', 'edits': value} for value in (None, '', '  \n', 17, {}, 'x' * 4001)],
            {**binding, 'decision': 'approve', 'action_hash': 'not-a-hash'},
            {**binding, 'decision': 'approve', 'action_hash': 'a' * 64 + '\n'},
            {**binding, 'decision': 'approve', 'proposal_id': []},
            {**binding, 'decision': 'approve', 'unexpected': True},
        ]:
            with self.subTest(body=body):
                self.assert_invalid_without_writes('/api/v1/reviews', body)

    def test_nested_document_properties_and_commit_keys_are_validated(self):
        for content in (None, [], {'author': 'demo'}, {'text': 7}, {'text': 'x', 'author': {}},
                        {'text': 'x', 'signed_at': None}, {'text': 'x', 'unexpected': 'persisted'}):
            with self.subTest(content=content):
                self.assert_invalid_without_writes('/api/v1/documents', {'patient': 'p-demo', 'encounter': 'e-demo', 'expected_version': 1, 'content': content})
        binding = self.binding(self.proposal())
        for key in (None, {}, '', 'short', 'x' * 129):
            with self.subTest(key=key):
                self.assert_invalid_without_writes('/api/v1/commits', {**binding, 'idempotency_key': key})

    def test_malformed_json_duplicate_keys_and_nonfinite_values_are_rejected(self):
        for raw in (
            b'{', b'null', b'[]', b'"string"', b'{"patient":"p-demo","encounter":"e-demo","patient":"p-other"}',
            b'{"patient":NaN,"encounter":"e-demo"}', b'{"patient":Infinity,"encounter":"e-demo"}',
            b'{"patient":"\\ud800","encounter":"e-demo"}', b'{"patient":"\xff","encounter":"e-demo"}',
        ):
            with self.subTest(raw=raw):
                self.assert_invalid_without_writes('/api/v1/proposals', raw=raw)
        self.assert_invalid_without_writes('/api/v1/proposals', raw=b'{}', headers={'Content-Type': 'text/plain'})
        self.assert_invalid_without_writes('/api/v1/proposals', raw=b'{}', headers={'Content-Length': '65537'})

    def test_integral_number_normalization_preserves_idempotent_replay(self):
        binding = self.binding(self.proposal())
        status, reviewed = self.request('/api/v1/reviews', {**binding, 'version': 1.0, 'decision': 'approve'})
        self.assertEqual(status, 200)
        self.assertEqual(reviewed['proposal']['status'], 'approved')
        status, committed = self.request('/api/v1/commits', {**binding, 'version': 1.0, 'idempotency_key': 'numeric-replay-key'})
        self.assertEqual(status, 200)
        status, replayed = self.request('/api/v1/commits', {**binding, 'version': 1, 'idempotency_key': 'numeric-replay-key'})
        self.assertEqual(status, 200)
        self.assertTrue(replayed['replayed'])
        self.assertEqual(replayed['result'], committed['result'])
        self.assertEqual(len(self.service.context('reviewer-demo')['results']), 1)

    def test_failures_and_abstention_are_http_200_with_persisted_outcomes(self):
        for scenario, outcome in (('failure', 'failed'), ('timeout', 'timeout'), ('invalid', 'failed'), ('abstain', 'abstained')):
            with self.subTest(scenario=scenario):
                status, response = self.request('/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo', 'scenario': scenario})
                self.assertEqual(status, 200)
                self.assertEqual(response['outcome'], outcome)
                self.assertNotIn('proposal', response)
        context = self.service.context('reviewer-demo')
        self.assertEqual(len(context['runs']), 4)
        self.assertFalse(context['proposals'])
        abstained = next(run for run in context['runs'] if run['outcome'] == 'abstained')
        self.assertEqual(abstained['abstain_reason'], 'synthetic insufficient evidence')

    def test_auth_scope_missing_resource_and_stale_state_are_distinct(self):
        status, _ = self.request('/api/v1/context', token='wrong')
        self.assertEqual(status, 401)
        status, _ = self.request('/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'}, token='demo-viewer-token')
        self.assertEqual(status, 403)
        binding = self.binding(self.proposal())
        status, _ = self.request('/api/v1/reviews', {**binding, 'proposal_id': 'missing-proposal', 'decision': 'approve'})
        self.assertEqual(status, 404)
        status, _ = self.request('/api/v1/reviews', {**binding, 'version': 2, 'decision': 'approve'})
        self.assertEqual(status, 409)

    def test_unexpected_get_and_post_failures_return_sanitized_json(self):
        for method, path, body in (
            ('context', '/api/v1/context', None),
            ('propose', '/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'}),
        ):
            with self.subTest(method=method), patch.object(self.service, method, side_effect=RuntimeError('secret internal detail')):
                status, response = self.request(path, body)
                self.assertEqual(status, 500)
                self.assertEqual(response, {'error': 'INTERNAL_ERROR'})
        status, health = self.request('/health')
        self.assertEqual(status, 200)
        self.assertTrue(health['demo'])


if __name__ == '__main__':
    unittest.main()
