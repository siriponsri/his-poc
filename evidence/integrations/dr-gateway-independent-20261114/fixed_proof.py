from pathlib import Path
import sys,json,hashlib,threading
from datetime import timedelta
from copy import deepcopy
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError

ROOT=Path('C:/Users/User/Desktop/myProject/his-poc')
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend/tests'))
from test_dr_gateway_pg import prepared,explicit_seed,BASE,png,login
from backend.tests.test_dr_client_unit import receipt
from backend.app import dr_gateway as gateway
from backend.app.common import uid,utcnow
from backend.app.db import SessionLocal
from backend.app.models_dr import DRAttempt,DRCapabilityGrant,DRCapabilityGrantEvent,DRBinding,DRExchange
from backend.app.dr_client import DRClient,DRUnknown
from backend.app.dr_protocol import canonical,digest


@pytest.mark.parametrize('fault',['wrong-original','case-html','foreign-case','foreign-list'])
def test_malformed_matching_envelopes_never_forwarded(prepared,fault):
    client,source_set,binding,receiver,body=prepared
    image=source_set['sources'][0]['image_sha256'];wrong_png=png('authored-independent-wrong-frame')
    original=receiver.envelope
    def malformed(value,workspace,data,kind):
        if fault=='wrong-original' and kind=='image/png':data=wrong_png
        elif fault=='case-html':data=b'<html><body>wrong representation</body></html>';kind='text/html'
        elif fault=='foreign-case':data=canonical({'image_id':'f'*64})
        elif fault=='foreign-list':data=canonical([{'image_id':'f'*64}])
        return original(value,workspace,data,kind)
    receiver.envelope=malformed
    path='/v1/images/'+image if fault=='wrong-original' else '/v1/cases' if fault=='foreign-list' else '/v1/cases/'+image
    response=client.get(f'/integrations/dr/{binding}/api'+path)
    assert response.status_code in {202,409,502},response.text
    assert response.content!=wrong_png and response.headers.get('content-type','').startswith('application/json')
    with SessionLocal() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
        assert attempt.status!='succeeded'
    print(json.dumps({'fixed':'MALFORMED_MATCHING_ENVELOPE_REJECTED','fault':fault,'status':response.status_code}))


def test_expired_mutation_lease_quarantines_and_fences_new_session(prepared):
    client,source_set,binding,receiver,body=prepared
    image=source_set['sources'][0]['image_sha256'];key=uid()
    def expire(value):
        with SessionLocal.begin() as db:
            attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation_key==key))
            attempt.lease_expires_at=utcnow()-timedelta(seconds=1)
    receiver.hook=expire
    response=client.post(f'/integrations/dr/{binding}/api/v1/cases/{image}/admission',
        json={'revision':0,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':key})
    assert response.status_code==409,response.text
    with SessionLocal() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation_key==key))
        assert attempt.status=='quarantined'
        assert db.get(DRBinding,binding).state=='quarantined'
        exchange=db.scalar(select(DRExchange).where(DRExchange.attempt_id==attempt.id))
        assert exchange.receipt is not None and exchange.outcome=='succeeded' and exchange.quarantined
    receiver.hook=None;calls=len(receiver.calls);other=login()
    retry=other.post(BASE+f"/source-sets/{source_set['id']}/bindings",json={'transfer_consent':body['transfer_consent']},headers={'Idempotency-Key':uid()})
    assert retry.status_code==409,retry.text
    assert len(receiver.calls)==calls
    print(json.dumps({'fixed':'EXPIRED_LEASE_QUARANTINED_NEW_SESSION_FENCED','status':response.status_code,'other_session_status':retry.status_code}))


def test_grant_revocation_serializes_and_history_is_immutable(prepared,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    with SessionLocal.begin() as db:
        grant=DRCapabilityGrant(organization_id='org-demo',facility_id='facility-demo',user_id='user-clinician',
            capability='dr.report.sign',status='active',valid_from=utcnow()-timedelta(minutes=1),
            valid_until=utcnow()+timedelta(hours=1),verification_status='verified',
            evidence_reference='synthetic-validation:independent-serialized-revocation',verifier_id='user-quality',version=1)
        db.add(grant);db.flush();grant_id=grant.id
    original=gateway.owned;calls=[];started=threading.Event();finished=threading.Event();errors=[];threads=[]
    def revoke():
        try:
            with SessionLocal.begin() as db:
                db.execute(text("SET LOCAL lock_timeout='3s'"))
                row=db.get(DRCapabilityGrant,grant_id);row.status='revoked';row.version+=1
                started.set();db.flush()
        except Exception as error:errors.append(repr(error))
        finally:finished.set()
    def owned(*args,**kwargs):
        result=original(*args,**kwargs);calls.append(1)
        if len(calls)==2:
            thread=threading.Thread(target=revoke,daemon=True);threads.append(thread);thread.start()
            assert started.wait(2),'Independent revoker did not reach its write'
            assert not finished.wait(.15),'Revocation committed while final authorization was reserved'
        return result
    monkeypatch.setattr(gateway,'owned',owned)
    image=source_set['sources'][0]['image_sha256'];key=uid()
    response=client.post(f'/integrations/dr/{binding}/api/v1/cases/{image}/admission',
        json={'revision':0,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':key})
    assert response.status_code==200,response.text
    assert finished.wait(3),'Revocation did not finish after HIS commit'
    for thread in threads:thread.join(1)
    assert not errors,errors
    with SessionLocal() as db:
        assert db.get(DRCapabilityGrant,grant_id).status=='revoked'
        events=db.scalars(select(DRCapabilityGrantEvent).where(DRCapabilityGrantEvent.grant_id==grant_id).order_by(DRCapabilityGrantEvent.grant_version)).all()
        assert [e.operation for e in events]==['INSERT','UPDATE']
        assert [e.grant_version for e in events]==[1,2]
        assert events[0].old_snapshot is None and events[0].new_snapshot['status']=='active'
        assert events[1].old_snapshot['status']=='active' and events[1].new_snapshot['status']=='revoked'
        assert all(e.database_principal=='his_test' for e in events)
        event_id=events[1].id
    history=client.get(BASE+f'/capability-grants/{grant_id}/history')
    assert history.status_code==200,history.text
    assert all(event['actor_user_id'] is None for event in history.json()['events'])
    with SessionLocal() as db:
        with pytest.raises(DBAPIError):db.execute(text('DELETE FROM dr_capability_grant_events WHERE id=:id'),{'id':event_id})
    print(json.dumps({'fixed':'GRANT_REVOCATION_SERIALIZED','immutable_event_versions':[1,2],'database_principal':'his_test','invented_human_actor':False}))


@pytest.mark.parametrize('fault',['missing-confirmation','missing-signer','wrong-eye-findings'])
def test_self_consistent_signed_current_requires_real_review_metadata(fault):
    destination,operation,value=receipt(signed=True)
    report=value['snapshot']['report'];witness=report['carebalance_review_witness']
    if fault=='missing-confirmation':witness['cases'][0].update(confirm_revision=None,grade_review_revision=None,grade_status='NOT_REVIEWED',reviewed_grade=None,quality='UNGRADABLE')
    elif fault=='missing-signer':
        report['carebalance_identity'].pop('actor_id',None);report['carebalance_identity'].pop('session_id',None)
        report['carebalance_identity'].pop('binding_id',None);report['signed_by'].pop('name',None)
    else:report['form']['left']['grade']=4
    witness['report_form_sha256']=digest(report['form'])
    report['carebalance_review_witness_sha256']=digest(witness)
    value['snapshot']['report_sha256']=digest(report);value['snapshot_sha256']=digest(value['snapshot'])
    value['review_freshness']['witness_sha256']=value['review_freshness']['current_witness_sha256']=digest(witness)
    with pytest.raises(DRUnknown):DRClient(destination).validate_report(value,operation)
    print(json.dumps({'fixed':'SELF_CONSISTENT_INVALID_SIGNED_CURRENT_DENIED','fault':fault}))
