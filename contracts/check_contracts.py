"""Optional schema/HTTP verification. Requires jsonschema==4.26.0; not runtime.

Use --write-fixtures only to refresh frozen synthetic frontend fixtures after an
intentional contract change. Normal verification never changes package files.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch
import urllib.error
import urllib.request

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.his_poc.request_validation import REQUEST_SCHEMAS, validate_request
from src.his_poc.server import make_server
from src.his_poc.service import DomainError, Service

C = ROOT / 'contracts/v1'
schemas = {p.name: json.loads(p.read_text(encoding='utf-8')) for p in C.glob('*.schema.json')}
registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas.values())
registry = registry.with_resources((n, Resource.from_contents(s)) for n, s in schemas.items())
api = json.loads((C / 'openapi.json').read_text(encoding='utf-8'))


def validator(schema):
    return Draft202012Validator(schema, registry=registry)


def validate(name, instance):
    validator(schemas[name + '.schema.json']).validate(instance)


def validate_http_response(record):
    operation = api['paths'][record['path']][record['method']]
    response = operation['responses'][str(record['status'])]
    validator(response['content']['application/json']['schema']).validate(record['response'])


def parity_cases():
    propose = {'patient': 'p-demo', 'encounter': 'e-demo'}
    binding = {'proposal_id': 'synthetic-proposal', 'version': 1, 'action_hash': 'a' * 64}
    review = {**binding, 'decision': 'approve'}
    commit = {**binding, 'idempotency_key': 'synthetic-key-001'}
    document = {'patient': 'p-demo', 'encounter': 'e-demo', 'expected_version': 1, 'content': {'text': 'synthetic'}}
    bases = dict(zip(REQUEST_SCHEMAS, (propose, review, commit, document)))
    for path, body in bases.items():
        yield path, body
        yield path, {**body, 'extra': 'forbidden'}
        for missing in body:
            yield path, {key: value for key, value in body.items() if key != missing}
        for value in (None, [], 'not-an-object', 1, True):
            yield path, value
    for version in (True, False, None, '1', 0, -1, 1.5, [], {}, 1.0, 2):
        yield '/api/v1/reviews', {**review, 'version': version}
        yield '/api/v1/commits', {**commit, 'version': version}
        yield '/api/v1/documents', {**document, 'expected_version': version}
    for decision in ('approve', 'reject', 'edit', 'unknown', [], True):
        yield '/api/v1/reviews', {**review, 'decision': decision}
        for edits in (None, '', ' \n', 'synthetic edited summary', 'x' * 4001, 17, {}):
            yield '/api/v1/reviews', {**review, 'decision': decision, 'edits': edits}
    for key in (None, [], '', 'short', 'x' * 128, 'x' * 129):
        yield '/api/v1/commits', {**commit, 'idempotency_key': key}
    for action_hash in (None, [], 1, '', 'A' * 64, 'a' * 63, 'a' * 65, 'a' * 64 + '\n'):
        yield '/api/v1/reviews', {**review, 'action_hash': action_hash}
        yield '/api/v1/commits', {**commit, 'action_hash': action_hash}
    for content in (None, [], {}, {'text': 1}, {'text': 'ok', 'author': {}},
                    {'text': 'ok', 'signed_at': None}, {'text': 'ok', 'extra': 'no'},
                    {'text': '', 'author': 'demo', 'signed_at': 'synthetic timestamp'}):
        yield '/api/v1/documents', {**document, 'content': content}
    for field in ('patient', 'encounter'):
        for value in (None, [], {}, 7, '', 'valid-synthetic-id'):
            yield '/api/v1/proposals', {**propose, field: value}
    for field, values in (('scenario', ('success', 'timeout', 'failure', 'invalid', 'abstain', 'unknown', [])),
                          ('data_class', ('synthetic', 'restricted', None, []))):
        for value in values:
            yield '/api/v1/proposals', {**propose, field: value}


def capture_http():
    records = []
    with tempfile.TemporaryDirectory() as directory:
        service = Service(Path(directory) / 'contract.sqlite3', {'inference_profile': 'mock_demo', 'provider': 'mock'})
        server = make_server(service, 0)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)

        def request(name, path, body=None, expected=200, token='demo-reviewer-token'):
            req = urllib.request.Request(base + path,
                data=json.dumps(body).encode('utf-8') if body is not None else None,
                headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            try:
                response = urllib.request.urlopen(req, timeout=7)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                record = {'name': name, 'method': 'post' if body is not None else 'get',
                          'path': path, 'status': response.status, 'response': json.load(response)}
            if body is not None:
                record['request'] = body
            assert record['status'] == expected, (name, record)
            validate_http_response(record)
            records.append(record)
            return record['response']

        def binding(proposal):
            return {'proposal_id': proposal['id'], 'version': proposal['version'], 'action_hash': proposal['action_hash']}

        try:
            request('health', '/health')
            request('context_initial', '/api/v1/context')
            request('document_updated', '/api/v1/documents', {'patient': 'p-demo', 'encounter': 'e-demo',
                    'expected_version': 1.0, 'content': {'text': 'Synthetic contract fixture document', 'author': 'demo-author'}})
            for scenario in ('failure', 'timeout', 'invalid', 'abstain'):
                request('proposal_' + scenario, '/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo', 'scenario': scenario})
            request('context_faults', '/api/v1/context')
            rejected = request('proposal_to_reject', '/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'})['proposal']
            request('review_rejected', '/api/v1/reviews', {**binding(rejected), 'decision': 'reject'})
            p = request('proposal_success', '/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'})['proposal']
            request('context_pending', '/api/v1/context')
            p = request('review_edited', '/api/v1/reviews', {**binding(p), 'decision': 'edit', 'edits': 'DEMO revised summary requiring a fresh review'})['proposal']
            request('context_edited', '/api/v1/context')
            request('commit_not_approved', '/api/v1/commits', {**binding(p), 'idempotency_key': 'contract-not-approved'}, 409)
            request('review_approved', '/api/v1/reviews', {**binding(p), 'decision': 'approve'})
            request('context_approved', '/api/v1/context')
            result = request('commit_created', '/api/v1/commits', {**binding(p), 'idempotency_key': 'contract-commit-001'})
            replay = request('commit_replayed', '/api/v1/commits', {**binding(p), 'version': float(p['version']), 'idempotency_key': 'contract-commit-001'})
            assert replay['replayed'] and replay['result'] == result['result']
            context = request('context_committed', '/api/v1/context')
            assert len(context['results']) == 1
            assert len(context['runs']) == 6
            for item in context['proposals']:
                validate('proposal', item)
                validate('document_completeness_action', json.loads(item['action']))
                validate('evidence_snapshot', json.loads(item['snapshot']))
            for item in context['reviews']:
                validate('review_record', item)
                json.loads(item['edits'])
            for item in context['audit']:
                validate('audit_event', item)
                json.loads(item['details'])
            request('error_unauthenticated', '/api/v1/context', expected=401, token='wrong')
            request('error_scope_denied', '/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'}, 403, token='demo-viewer-token')
            request('error_not_found', '/api/v1/reviews', {**binding(p), 'proposal_id': 'missing-proposal', 'decision': 'approve'}, 404)
            request('error_invalid_request', '/api/v1/reviews', {**binding(p), 'version': True, 'decision': 'approve'}, 400)
            request('error_stale_version', '/api/v1/reviews', {**binding(p), 'version': p['version'] + 1, 'decision': 'approve'}, 409)
            with patch.object(service, 'context', side_effect=RuntimeError('synthetic internal failure')):
                request('error_internal_get', '/api/v1/context', expected=500)
            with patch.object(service, 'propose', side_effect=RuntimeError('synthetic internal failure')):
                request('error_internal_post', '/api/v1/proposals', {'patient': 'p-demo', 'encounter': 'e-demo'}, 500)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-fixtures', action='store_true')
    args = parser.parse_args()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    examples = list((C / 'examples').glob('*.json'))
    for example in examples:
        validate(example.stem, json.loads(example.read_text(encoding='utf-8')))
    for path, operations in api['paths'].items():
        for operation in operations.values():
            for response in operation['responses'].values():
                reference = response['content']['application/json']['schema']['$ref']
                assert reference in schemas, (path, reference)
    parity_count = 0
    for path, body in parity_cases():
        expected = validator(schemas[REQUEST_SCHEMAS[path] + '.schema.json']).is_valid(body)
        try:
            validate_request(path, body)
            actual = True
        except DomainError as exc:
            assert exc.status == 400
            actual = False
        assert expected == actual, ('request-schema parity', path, body, expected, actual)
        parity_count += 1
    records = capture_http()
    fixture_path = C / 'fixtures/workflow.json'
    if args.write_fixtures:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps({'fixture_kind': 'FROZEN_SYNTHETIC_HTTP_RESPONSES',
            'source': 'Local stdlib HTTP server with explicit mock provider; no browser or live inference.',
            'api_contract_version': api['info']['version'], 'responses': records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    frozen = json.loads(fixture_path.read_text(encoding='utf-8'))
    for record in frozen['responses']:
        validate_http_response(record)
    print(json.dumps({'status': 'PASS', 'schema_count': len(schemas), 'example_count': len(examples),
        'request_parity_cases': parity_count, 'http_response_count': len(records),
        'frozen_response_count': len(frozen['responses']),
        'runtime_shapes': ['health_response', 'context_response', 'propose_response', 'review_response',
            'document_update_response', 'commit_response', 'error', 'proposal', 'document_completeness_action',
            'evidence_snapshot', 'review_record', 'audit_event'],
        'jsonschema_version': importlib.metadata.version('jsonschema'),
        'live_provider_tested': False, 'browser_tested': False}))


if __name__ == '__main__':
    main()
