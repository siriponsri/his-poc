"""Authorized patient display metadata on a disposable PostgreSQL database."""
import os

assert os.environ.get('HIS_TEST_DATABASE_URL') and os.environ['HIS_TEST_DATABASE_URL']==os.environ.get('DATABASE_URL'), 'Disposable PostgreSQL wrapper required'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import SessionLocal, engine
from backend.app.main import app
from backend.app.models import CareAssignment, Patient, PatientIdentifier
from backend.app.seed import seed


@pytest.fixture(scope='module',autouse=True)
def isolated_patients():
    assert engine.url.database=='his_test'
    with SessionLocal.begin() as db:
        seed(db,os.environ['HIS_SEED_PASSWORD'])
        db.add_all([
            Patient(id='patient-presentation-unassigned',organization_id='org-demo',facility_id='facility-demo',display_name='Unassigned fictional presentation record'),
            Patient(id='patient-presentation-no-identifier',organization_id='org-demo',facility_id='facility-demo',display_name='Fictional record without identifier'),
        ])
        db.flush()
        db.add_all([
            PatientIdentifier(id='presentation-hn',patient_id='patient-001',organization_id='org-demo',issuer='CAREBALANCE_DEMO',value='06901425'),
            PatientIdentifier(id='presentation-cross-org',patient_id='patient-other',organization_id='org-other',issuer='HN',value='OTHER_ORGANIZATION_HN'),
            PatientIdentifier(id='presentation-cross-facility',patient_id='patient-second',organization_id='org-demo',issuer='HN',value='OTHER_FACILITY_HN'),
            PatientIdentifier(id='presentation-unassigned',patient_id='patient-presentation-unassigned',organization_id='org-demo',issuer='HN',value='UNASSIGNED_HN'),
            CareAssignment(user_id='user-clinician',patient_id='patient-presentation-no-identifier'),
        ])


def login(username):
    client=TestClient(app)
    response=client.post('/api/v2/auth/login',json={'username':username,'password':os.environ['HIS_SEED_PASSWORD']})
    assert response.status_code==200,response.text
    return client


def test_full_patient_list_returns_actual_identifier_values_without_renaming_ids():
    with SessionLocal() as db:
        before=[(row.id,row.issuer,row.value) for row in db.scalars(select(PatientIdentifier).where(PatientIdentifier.patient_id=='patient-001').order_by(PatientIdentifier.id))]
    with login('clinician') as client:
        response=client.get('/api/v2/patients')
        assert response.status_code==200
        patients={row['id']:row for row in response.json()['items']}
        assert set(patients)=={'patient-001','patient-002','patient-003','patient-004','patient-presentation-no-identifier'}
        assert patients['patient-001']['identifiers']==[
            {'issuer':'CAREBALANCE_DEMO','value':'06901425'},
            {'issuer':'SYNTHETIC','value':'SYN-001'},
        ]
        assert all(set(identifier)=={'issuer','value'} for row in patients.values() for identifier in row['identifiers'])
        assert patients['patient-presentation-no-identifier']['identifiers']==[]
        assert 'birth_date' in patients['patient-001'] and 'sex' in patients['patient-001']
        detail=client.get('/api/v2/patients/patient-001').json()
        assert detail['id']=='patient-001'
        assert {(value['issuer'],value['value']) for value in detail['identifiers']}=={('CAREBALANCE_DEMO','06901425'),('SYNTHETIC','SYN-001')}
    with SessionLocal() as db:
        after=[(row.id,row.issuer,row.value) for row in db.scalars(select(PatientIdentifier).where(PatientIdentifier.patient_id=='patient-001').order_by(PatientIdentifier.id))]
    assert after==before


def test_full_identifier_projection_retains_patient_facility_and_organization_scope():
    with login('clinician') as client:
        response=client.get('/api/v2/patients')
        assert response.status_code==200
        for hidden in ['OTHER_ORGANIZATION_HN','OTHER_FACILITY_HN','UNASSIGNED_HN']:
            assert hidden not in response.text
        for identity in ['patient-other','patient-second','patient-presentation-unassigned']:
            assert client.get('/api/v2/patients/'+identity).status_code==404
        filtered=client.get('/api/v2/patients',params={'q':'without identifier'}).json()['items']
        assert [row['id'] for row in filtered]==['patient-presentation-no-identifier']
        assert filtered[0]['identifiers']==[]


@pytest.mark.parametrize('username',['finance','clinician','patient'])
def test_minimum_patient_references_never_expand_demographics_or_identifiers(username):
    with login(username) as client:
        response=client.get('/api/v2/reference/patients')
        assert response.status_code==200
        assert response.json()['access']=='minimum_reference_metadata'
        assert response.json()['items']
        assert all(set(row)=={'id','display_name','status'} for row in response.json()['items'])
        assert all(value not in response.text for value in ['06901425','SYN-001','OTHER_ORGANIZATION_HN','OTHER_FACILITY_HN','UNASSIGNED_HN'])
        if username=='patient':assert [row['id'] for row in response.json()['items']]==['patient-001']


def test_reference_only_and_anonymous_accounts_cannot_request_full_patient_metadata():
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/v2/patients').status_code==401
    for username in ['finance','patient']:
        with login(username) as client:
            assert client.get('/api/v2/patients').status_code==403
            assert client.get('/api/v2/patients/patient-001').status_code==403
