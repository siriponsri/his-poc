"""Additional canonical ERP acceptance on an explicit disposable PostgreSQL DB."""
import os
import uuid
from collections import Counter
from datetime import datetime
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import Encounter, SecurityEvent
from backend.app.models_erp import Charge, InvoiceAdjustment, Remittance, StockBalance, StockMovement
from backend.app.seed import seed


def key():
    return str(uuid.uuid4())


@pytest.fixture(scope='module', autouse=True)
def synthetic_database():
    if not os.environ.get('HIS_TEST_DATABASE_URL'):
        pytest.skip('Explicit disposable PostgreSQL test URL required')
    assert os.environ['HIS_TEST_DATABASE_URL'] == os.environ['DATABASE_URL']
    assert os.environ['DATABASE_URL'].startswith('postgresql')
    command.upgrade(Config('backend/alembic.ini'), 'head')
    with SessionLocal.begin() as db:
        seed(db, os.environ['HIS_SEED_PASSWORD'])


@pytest.fixture
def actors(synthetic_database):
    clients = {}
    for role in ['billing', 'inventory', 'quality', 'nurse']:
        client = TestClient(app)
        login = client.post('/api/v2/auth/login', json={
            'username': role, 'password': os.environ['HIS_SEED_PASSWORD']})
        assert login.status_code == 200, login.text
        client.headers['X-CSRF-Token'] = login.json()['csrf_token']
        clients[role] = client
    yield clients
    for client in clients.values():
        client.close()


def post(client, path, payload, *, operation_key=None, expected=200):
    response = client.post('/api/v2' + path, json=payload,
                           headers={'Idempotency-Key': operation_key or key()})
    assert response.status_code == expected, (path, response.status_code, response.text)
    return response.json()


def action(client, domain, row, name, **values):
    return post(client, f'/erp/{domain}/records/{row["id"]}/actions',
                {'version': row['version'], 'action': name, **values})


def invoice(client):
    charge = post(client, '/erp/charges', {
        'encounter_id': 'encounter-001', 'source_id': key(),
        'label': 'Synthetic acceptance service', 'quantity': '1',
        'price_version_id': 'price-demo'})
    row = post(client, '/erp/D23/records', {
        'encounter_id': 'encounter-001', 'label': 'Synthetic acceptance invoice'})
    for name in ['price', 'review', 'invoice']:
        row = action(client, 'D23', row, name)
    return row, charge


def submitted_claim(client, invoice_row):
    row = post(client, '/erp/D24/records', {
        'invoice_id': invoice_row['id'], 'payer_name': 'Synthetic acceptance payer'})
    for name in ['validate', 'export', 'simulate_submit']:
        row = action(client, 'D24', row, name)
    return row


def test_d28_transfer_conserves_lot_and_same_key_replays_once(actors):
    client = actors['inventory']
    lot = post(client, '/erp/lots', {
        'item_id': 'item-demo', 'lot_number': 'ACCEPT-' + key(),
        'expiry_date': '2035-12-31', 'unit_cost': '2.00'})
    row = post(client, '/erp/D28/records', {
        'lot_id': lot['id'], 'location_id': 'stock-main',
        'quantity': '10', 'source_id': key()})
    row = action(client, 'D28', row, 'validate')
    posted = action(client, 'D28', row, 'post')
    path = f'/erp/D28/records/{posted["id"]}/actions'
    payload = {'version': posted['version'], 'action': 'transfer',
               'quantity': '4', 'location_id': 'stock-ward'}
    operation_key = key()
    transferred = post(client, path, payload, operation_key=operation_key)
    assert post(client, path, payload, operation_key=operation_key) == transferred
    with SessionLocal() as db:
        balances = list(db.scalars(select(StockBalance).where(StockBalance.lot_id == lot['id'])))
        assert {b.location_id: b.available for b in balances} == {
            'stock-main': Decimal('6'), 'stock-ward': Decimal('4')}
        assert sum(b.available + b.quarantined for b in balances) == Decimal('10')
        movements = list(db.scalars(select(StockMovement).where(
            StockMovement.lot_id == lot['id'], StockMovement.status == 'posted')))
        legs = [m for m in movements if m.source_id == posted['id']]
        assert len(legs) == 2
        assert {(m.location_id, m.quantity) for m in legs} == {
            ('stock-main', Decimal('-4')), ('stock-ward', Decimal('4'))}
        assert {m.operation_key for m in legs} == {operation_key + ':out', operation_key + ':in'}
        assert sum(m.quantity for m in movements) == Decimal('10')
        assert db.get(StockMovement, posted['id']).quantity == Decimal('10')


def test_d24_duplicate_remittance_source_does_not_change_second_claim(actors):
    client = actors['billing']
    first_invoice, _ = invoice(client)
    first = submitted_claim(client, first_invoice)
    source_key = 'REMIT-' + key()
    first = action(client, 'D24', first, 'remittance',
                   approved_amount='800.00', source_key=source_key)
    second_invoice, _ = invoice(client)
    second = submitted_claim(client, second_invoice)
    before = client.get('/api/v2/erp/D24/records/' + second['id']).json()
    post(client, f'/erp/D24/records/{second["id"]}/actions', {
        'version': second['version'], 'action': 'remittance',
        'approved_amount': '800.00', 'source_key': source_key}, expected=409)
    after = client.get('/api/v2/erp/D24/records/' + second['id']).json()
    assert after == before
    assert after['status'] == 'simulated_submitted'
    assert Decimal(after['approved']) == 0
    assert Decimal(first['approved']) == 800
    assert Decimal(first['financials']['gross_received']) == 0
    assert Decimal(first['financials']['net_received']) == 0
    with SessionLocal() as db:
        records = list(db.scalars(select(Remittance).where(Remittance.source_key == source_key)))
        assert len(records) == 1
        assert records[0].claim_id == first['id']
        assert records[0].approved_amount == Decimal('800')
        assert db.scalar(select(func.count()).select_from(Remittance).where(
            Remittance.claim_id == second['id'])) == 0


def test_d23_duplicate_charge_source_and_adjustment_replay_preserve_original(actors):
    client = actors['billing']
    source_id = key()
    values = {'encounter_id': 'encounter-001', 'source_id': source_id,
              'label': 'Synthetic duplicate source', 'quantity': '1',
              'price_version_id': 'price-demo'}
    charge = post(client, '/erp/charges', values)
    duplicate = post(client, '/erp/charges', values)
    # A different operation key reloads the same DB row; numeric scale and
    # session timezone formatting may differ without creating a new charge.
    assert {k: duplicate[k] for k in ['id', 'version', 'source_id', 'encounter_id']} == {
        k: charge[k] for k in ['id', 'version', 'source_id', 'encounter_id']}
    for field in ['quantity', 'unit_price', 'amount']:
        assert Decimal(duplicate[field]) == Decimal(charge[field])
    assert datetime.fromisoformat(duplicate['created_at']) == datetime.fromisoformat(charge['created_at'])
    row = post(client, '/erp/D23/records', {
        'encounter_id': 'encounter-001', 'label': 'Synthetic adjustment acceptance'})
    for name in ['price', 'review', 'invoice']:
        row = action(client, 'D23', row, name)
    original = client.get('/api/v2/erp/D23/records/' + row['id']).json()
    original_charge = next(c for c in original['charges'] if c['id'] == charge['id'])
    path = f'/erp/D23/records/{row["id"]}/actions'
    payload = {'version': row['version'], 'action': 'adjust',
               'original_charge_id': charge['id'], 'amount': '-100.00',
               'reason': 'Synthetic referenced credit'}
    operation_key = key()
    adjusted = post(client, path, payload, operation_key=operation_key)
    assert post(client, path, payload, operation_key=operation_key) == adjusted
    assert adjusted['billed'] == original['billed']
    assert Decimal(adjusted['financials']['adjustments']) == Decimal('-100')
    assert next(c for c in adjusted['charges'] if c['id'] == charge['id']) == original_charge
    assert len(adjusted['adjustments']) == 1
    adjustment = adjusted['adjustments'][0]
    assert adjustment['original_charge_id'] == charge['id']
    assert adjustment['invoice_id'] == row['id']
    assert adjustment['approver_id'] == 'user-billing'
    assert adjustment['reason'] == payload['reason']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Charge).where(Charge.source_id == source_id)) == 1
        assert db.scalar(select(func.count()).select_from(InvoiceAdjustment).where(
            InvoiceAdjustment.invoice_id == row['id'])) == 1
        assert db.get(Charge, charge['id']).amount == Decimal('1000')


def test_d33_every_lineage_resolves_and_exported_batch_survives_correction(actors):
    client = actors['quality']
    report = post(client, '/erp/D33/records', {
        'name': 'Synthetic complete lineage',
        'period_start': '2020-01-01', 'period_end': '2035-12-31'})
    for name in ['generate', 'review', 'export']:
        report = action(client, 'D33', report, name)
    original = client.get('/api/v2/erp/D33/records/' + report['id']).json()
    assert original['status'] == 'exported'
    assert len(original['lineage']) == original['summary']['total_encounters'] > 0
    counts = Counter()
    with SessionLocal() as db:
        for link in original['lineage']:
            source = db.get(Encounter, link['encounter_id'])
            assert source is not None
            assert source.organization_id == original['organization_id']
            assert source.facility_id == original['facility_id']
            assert source.version == link['source_version']
            assert source.status == link['source_status']
            assert link['batch_id'] == original['id']
            counts[source.status] += 1
    assert dict(counts) == original['summary']['by_status']
    # The correction must observe changed current data while retaining the old export.
    changed_source_id = original['lineage'][0]['encounter_id']
    with SessionLocal.begin() as db:
        source = db.get(Encounter, changed_source_id)
        source.version += 1
        new_version = source.version
    corrected = action(client, 'D33', report, 'correct')
    assert corrected['id'] != report['id'] and corrected['original_id'] == report['id']
    corrected = action(client, 'D33', corrected, 'generate')
    assert next(link for link in corrected['lineage'] if link['encounter_id'] == changed_source_id)['source_version'] == new_version
    assert client.get('/api/v2/erp/D33/records/' + report['id']).json() == original


def test_d30_suspended_credential_denial_has_scoped_security_audit(actors):
    quality, nurse = actors['quality'], actors['nurse']
    roster = post(quality, '/erp/D30/records', {
        'staff_id': 'staff-nurse', 'starts_at': '2033-01-01T08:00:00Z',
        'ends_at': '2033-01-01T16:00:00Z'})
    for name in ['review', 'publish']:
        roster = action(quality, 'D30', roster, name)
    staff = next(row for row in quality.get('/api/v2/erp/staff').json()['items']
                 if row['id'] == 'staff-nurse')
    credential_path = '/erp/staff/staff-nurse/credential'
    suspended = post(quality, credential_path, {
        'version': staff['version'], 'status': 'suspended',
        'reason': 'Synthetic credential audit acceptance'})
    # Included routers expose their local templated path in request.scope.route.
    route = '/erp/D30/records/{record_id}/actions'
    with SessionLocal() as db:
        before_ids = set(db.scalars(select(SecurityEvent.id)))
    try:
        post(nurse, f'/erp/D30/records/{roster["id"]}/actions', {
            'version': roster['version'], 'action': 'acknowledge'}, expected=403)
        with SessionLocal() as db:
            added = list(db.scalars(select(SecurityEvent).where(
                SecurityEvent.id.not_in(before_ids)))) if before_ids else list(db.scalars(select(SecurityEvent)))
            assert len(added) == 1
            event = added[0]
            assert event.actor_id == 'user-nurse'
            assert event.organization_id == 'org-demo'
            assert event.facility_id == 'facility-demo'
            assert event.method == 'POST'
            assert event.route_template == route
            assert event.status_code == 403
            assert event.event == 'request_denied_or_rejected'
            # Security events are bounded metadata, not raw request/credential logs.
            columns = {column.name for column in SecurityEvent.__table__.columns}
            assert not columns.intersection({'body', 'request_body', 'headers', 'cookie', 'password', 'csrf_token'})
            stored = {column: getattr(event, column) for column in columns}
            assert os.environ['HIS_SEED_PASSWORD'] not in str(stored)
            assert roster['id'] not in str(stored)  # Route template excludes submitted entity ID.
        unchanged = quality.get('/api/v2/erp/D30/records/' + roster['id']).json()
        assert unchanged['version'] == roster['version'] and unchanged['status'] == 'published'
    finally:
        post(quality, credential_path, {
            'version': suspended['version'], 'status': 'active',
            'reason': 'Synthetic explicit credential reactivation'})
    acknowledged = action(nurse, 'D30', roster, 'acknowledge')
    assert acknowledged['status'] == 'acknowledged'
