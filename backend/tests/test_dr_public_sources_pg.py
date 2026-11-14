"""Public provenance/consent guards with authored fixtures, not dataset claims."""
import os

assert os.getenv('HIS_TEST_DATABASE_URL')==os.environ.get('DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL')

from fastapi import HTTPException
import pytest
from sqlalchemy.exc import DBAPIError

from backend.app.common import uid
from backend.app.db import SessionLocal
from backend.app.dr_core import register_public_dataset_source,source_snapshot
from backend.app.models_clinical import ImagingStudy
from backend.app.models_dr import DRSourceProvenance
from backend.app.storage import file_store
from backend.tests.test_dr_gateway_pg import BASE,explicit_seed,fixture_sources,login,public_evidence


def register(selection,evidence=None,laterality='L'):
    with SessionLocal.begin() as db:
        source=db.get(ImagingStudy,selection['source_id'])
        return register_public_dataset_source(db,source_id=source.id,source_version=source.version,
            original_bytes=file_store().read(source.file_path,source.file_sha256),laterality=laterality,
            modality='CFP',capture_time=None,dataset_provenance=evidence or public_evidence(),
            registrar_id='user-operations_admin').id


def test_public_registration_is_immutable_scoped_and_not_an_inferred_eye():
    body=fixture_sources(registered=False);selection=body['sources'][0]
    with pytest.raises(HTTPException):register(selection,laterality=None)
    missing=public_evidence();missing['laterality_evidence_reference']=''
    with pytest.raises(HTTPException):register(selection,evidence=missing)
    provenance_id=register(selection)
    assert register(selection)==provenance_id
    other=public_evidence();other['membership_reference']='changed'
    with pytest.raises(HTTPException):register(selection,evidence=other)
    with SessionLocal() as db:
        row=db.get(DRSourceProvenance,provenance_id);source=db.get(ImagingStudy,selection['source_id'])
        assert row.source_origin=='PUBLIC'
        snapshot=source_snapshot(source,row)
        assert snapshot['schema']=='carebalance.his-dr-source.v2'
        assert snapshot['public_source']['dataset_provenance']==public_evidence()
    with pytest.raises(DBAPIError):
        with SessionLocal.begin() as db:
            row=db.get(DRSourceProvenance,provenance_id);row.dataset_provenance={**public_evidence(),'attribution':'rewritten'}


def test_public_source_set_requires_v2_consent_and_retains_attribution():
    client=login();body=fixture_sources(registered=False);selection=body['sources'][0]
    selection['provenance_id']=register(selection)
    old=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()})
    assert old.status_code==422 and old.json()['detail']['code']=='DR_PUBLIC_TRANSFER_WORDING_REQUIRED'
    body['transfer_consent']['wording_version']='carebalance.dr-transfer.v2'
    result=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()})
    assert result.status_code==200,result.text
    manifest=result.json()['sources'][0]
    assert manifest['source_origin']=='PUBLIC' and manifest['media_type']=='image/png'
    rows=client.get(BASE+'/sources',params={'patient_id':body['patient_id'],'encounter_id':body['encounter_id']}).json()['items']
    source=next(item for item in rows if item['source_id']==selection['source_id'])
    assert source['dataset_provenance']==public_evidence()
    preview=client.get(source['preview_url'])
    assert preview.status_code==200 and preview.headers['content-type']=='image/png'


def test_public_hash_membership_is_not_claimed_without_matching_image_bytes():
    body=fixture_sources(registered=False);evidence=public_evidence()
    evidence.update(membership_basis='upstream_hash_match',upstream_image_sha256='a'*64)
    with pytest.raises(HTTPException):register(body['sources'][0],evidence=evidence)


def test_isolated_public_images_cannot_be_added_to_an_existing_patient_group():
    body=fixture_sources(registered=False);register(body['sources'][0])
    other=fixture_sources(registered=False);evidence=public_evidence()
    evidence['patient_grouping']='isolated_demo_record'
    with pytest.raises(HTTPException) as error:register(other['sources'][0],evidence=evidence)
    assert error.value.detail['code']=='DR_PUBLIC_PATIENT_GROUP_EVIDENCE_REQUIRED'
    evidence.update(patient_grouping='documented_same_patient',patient_grouping_reference='another-patient-group')
    with pytest.raises(HTTPException):register(other['sources'][0],evidence=evidence)
