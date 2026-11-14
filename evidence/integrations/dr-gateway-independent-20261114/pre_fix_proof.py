import os,sys,json,hashlib
from pathlib import Path
from datetime import timedelta
from copy import deepcopy
import pytest
from sqlalchemy import select

ROOT=Path('C:/Users/User/Desktop/myProject/his-poc')
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend/tests'))
from test_dr_gateway_pg import prepared,explicit_seed,BASE,png
from backend.app import dr_gateway as gateway
from backend.app.common import uid,utcnow
from backend.app.db import SessionLocal
from backend.app.models_dr import DRAttempt,DRCapabilityGrant,DRBinding
from backend.app.dr_client import patient_key
from backend.app.dr_protocol import WorkspaceScope


def test_original_image_wrong_bytes_accepted(prepared):
    client,source_set,binding,receiver,body=prepared
    image=source_set['sources'][0]['image_sha256']
    wrong_png=png('authored-independent-wrong-original-frame')
    assert hashlib.sha256(wrong_png).hexdigest()!=image
    envelope=receiver.envelope
    def wrong(value,workspace,data,kind):
        if kind=='image/png':data=wrong_png
        return envelope(value,workspace,data,kind)
    receiver.envelope=wrong
    response=client.get(f'/integrations/dr/{binding}/api/v1/images/{image}')
    actual=hashlib.sha256(response.content).hexdigest()
    assert response.status_code==200,response.text
    assert response.content==wrong_png and actual!=image
    with SessionLocal() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
        assert attempt.status=='succeeded'
    print(json.dumps({'finding':'WRONG_ORIGINAL_FRAME_ACCEPTED','status':response.status_code,
                      'selected_image_sha256':image,'returned_image_sha256':actual,'attempt_status':'succeeded'}))


def test_grant_revocation_after_final_read_not_serialized(prepared,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    with SessionLocal.begin() as db:
        grant=DRCapabilityGrant(organization_id='org-demo',facility_id='facility-demo',user_id='user-clinician',
            capability='dr.report.sign',status='active',valid_from=utcnow()-timedelta(minutes=1),
            valid_until=utcnow()+timedelta(hours=1),verification_status='verified',
            evidence_reference='synthetic-validation:independent-revocation-race',verifier_id='user-quality',version=1)
        db.add(grant);db.flush();grant_id=grant.id
    original=gateway.owned;calls=[]
    def owned(*args,**kwargs):
        values=original(*args,**kwargs);calls.append(1)
        if len(calls)==2:
            with SessionLocal.begin() as other:
                row=other.get(DRCapabilityGrant,grant_id);row.status='revoked';row.version+=1
        return values
    monkeypatch.setattr(gateway,'owned',owned)
    image=source_set['sources'][0]['image_sha256']
    key=uid()
    response=client.put(f'/integrations/dr/{binding}/api/v1/cases/{image}/screening-report',
        json={'revision':0,'sign':True,'report':{'hn':patient_key(WorkspaceScope(**source_set['scope']))}},
        headers={'Idempotency-Key':key})
    assert response.status_code==200,response.text
    with SessionLocal() as db:
        assert db.get(DRCapabilityGrant,grant_id).status=='revoked'
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation_key==key))
        assert attempt.status=='succeeded' and db.get(DRBinding,binding).state=='imported'
    print(json.dumps({'observation':'GRANT_REVOKED_AFTER_FINAL_AUTH_READ_BEFORE_COMMIT','status':response.status_code,
                      'grant_status':'revoked','attempt_status':'succeeded','receiver':'signed MockTransport, not real clinical receiver'}))


def test_expired_lease_receipt_finalized(prepared):
    client,source_set,binding,receiver,body=prepared
    def expire(value):
        with SessionLocal.begin() as db:
            attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
            attempt.lease_expires_at=utcnow()-timedelta(seconds=1)
    receiver.hook=expire
    response=client.get(f'/integrations/dr/{binding}/api/v1/cases')
    assert response.status_code==200,response.text
    with SessionLocal() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
        assert attempt.status=='succeeded' and attempt.lease_expires_at<utcnow()
    print(json.dumps({'observation':'EXPIRED_UNREPLACED_LEASE_FINALIZED','status':response.status_code,
                      'attempt_status':'succeeded','lease_expired':True}))
