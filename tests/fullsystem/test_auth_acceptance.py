"""Additional real PostgreSQL session-profile and login-throttle acceptance."""
import os
import uuid
from http.cookies import SimpleCookie

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.auth import COOKIE
from backend.app.common import text_hash
from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import LoginAttempt, Patient
from backend.app.seed import seed


@pytest.fixture(scope='module', autouse=True)
def synthetic_database():
    if not os.environ.get('HIS_TEST_DATABASE_URL'):
        pytest.skip('Requires explicitly disposable PostgreSQL')
    command.upgrade(Config('backend/alembic.ini'), 'head')
    with SessionLocal.begin() as db:
        seed(db, os.environ['HIS_SEED_PASSWORD'])


@pytest.mark.parametrize('secure,origin', [(False, 'http://127.0.0.1:8000'),
                                          (True, 'https://his.synthetic.test')])
def test_cookie_profiles_csrf_and_logout_replay(monkeypatch, secure, origin):
    monkeypatch.setenv('HIS_COOKIE_SECURE', str(secure).lower())
    monkeypatch.setenv('HIS_ALLOWED_ORIGINS', origin)
    with TestClient(app, base_url=origin) as client:
        response = client.post('/api/v2/auth/login', json={
            'username': 'registration', 'password': os.environ['HIS_SEED_PASSWORD']},
            headers={'Origin': origin})
        assert response.status_code == 200
        cookie = SimpleCookie(response.headers['set-cookie'])[COOKIE]
        assert cookie['httponly'] and cookie['samesite'].lower() == 'strict'
        assert bool(cookie['secure']) is secure
        assert cookie['path'] == '/'
        assert client.get('/api/v2/auth/me').status_code == 200
        operation = str(uuid.uuid4())
        payload = {'display_name': 'Synthetic CSRF negative', 'identifier': operation, 'sex': 'unknown'}
        assert client.post('/api/v2/patients', json=payload,
                           headers={'Idempotency-Key': operation}).status_code == 403
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(Patient).where(
                Patient.display_name == payload['display_name'])) == 0
        token = client.cookies.get(COOKIE)
        csrf = response.json()['csrf_token']
        assert client.post('/api/v2/auth/logout', headers={'X-CSRF-Token': csrf}).status_code == 200
        client.cookies.set(COOKIE, token)
        assert client.get('/api/v2/auth/me').status_code == 401


def test_unknown_account_failure_is_generic_and_throttled():
    username = 'synthetic-absent-' + uuid.uuid4().hex
    password = 'Synthetic incorrect password'
    with TestClient(app) as client:
        for _ in range(10):
            response = client.post('/api/v2/auth/login', json={'username': username, 'password': password})
            assert response.status_code == 401
            assert response.json() == {'detail': {'code': 'INVALID_CREDENTIALS'}}
        blocked = client.post('/api/v2/auth/login', json={'username': username, 'password': password})
        assert blocked.status_code == 429
        assert blocked.json() == {'detail': {'code': 'LOGIN_RATE_LIMITED'}}
        with SessionLocal() as db:
            attempts = list(db.scalars(select(LoginAttempt).where(
                LoginAttempt.identity_hash == text_hash(username.lower()))))
            assert len(attempts) == 10 and not any(row.successful for row in attempts)
            assert all(username not in str(row.__dict__) and password not in str(row.__dict__)
                       for row in attempts)
