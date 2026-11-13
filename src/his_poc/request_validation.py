"""Small stdlib HTTP validators for the four implemented v1 request contracts.

JSON Schema's integer type includes integral JSON numbers such as 1.0. Normalize
those values before service comparisons and idempotency hashing; bool is never
an integer version. Keep changes paired with contracts/v1 and contract checks.
"""
import math
import re

from .service import DomainError


REQUEST_SCHEMAS = {
    '/api/v1/proposals': 'propose_request',
    '/api/v1/reviews': 'review_request',
    '/api/v1/commits': 'commit_request',
    '/api/v1/documents': 'document_update_request',
}


def invalid():
    raise DomainError('INVALID_REQUEST', 400)


def object_keys(value, required, optional=()):
    if type(value) is not dict:
        invalid()
    keys = set(value)
    if not set(required) <= keys or keys - set(required) - set(optional):
        invalid()


def string(value, minimum=0, maximum=None):
    if type(value) is not str or len(value) < minimum:
        invalid()
    if maximum is not None and len(value) > maximum:
        invalid()
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        invalid()


def version(value):
    if type(value) is int and value >= 1:
        return value
    if type(value) is float and math.isfinite(value) and value >= 1 and value.is_integer():
        return int(value)
    invalid()


def validate_request(path, body):
    """Validate without persistence and return a normalized shallow copy."""
    if path not in REQUEST_SCHEMAS:
        raise DomainError('NOT_FOUND', 404)
    if path == '/api/v1/proposals':
        object_keys(body, ('patient', 'encounter'), ('scenario', 'data_class'))
        string(body['patient'], 1)
        string(body['encounter'], 1)
        if body.get('scenario', 'success') not in ('success', 'timeout', 'failure', 'invalid', 'abstain'):
            invalid()
        if body.get('data_class', 'synthetic') != 'synthetic':
            invalid()
        return dict(body)
    if path == '/api/v1/documents':
        object_keys(body, ('patient', 'encounter', 'expected_version', 'content'))
        string(body['patient'], 1)
        string(body['encounter'], 1)
        object_keys(body['content'], ('text',), ('author', 'signed_at'))
        for value in body['content'].values():
            string(value)
        return {**body, 'expected_version': version(body['expected_version'])}
    required = ('proposal_id', 'version', 'action_hash')
    if path == '/api/v1/reviews':
        object_keys(body, (*required, 'decision'), ('edits',))
        if body['decision'] not in ('approve', 'reject', 'edit'):
            invalid()
        if body['decision'] == 'edit':
            if 'edits' not in body:
                invalid()
            string(body['edits'], 1, 4000)
            if not body['edits'].strip():
                invalid()
        elif 'edits' in body:
            invalid()
    else:
        object_keys(body, (*required, 'idempotency_key'))
        string(body['idempotency_key'], 8, 128)
    string(body['proposal_id'], 1)
    string(body['action_hash'])
    if re.fullmatch(r'[a-f0-9]{64}', body['action_hash']) is None:
        invalid()
    return {**body, 'version': version(body['version'])}
