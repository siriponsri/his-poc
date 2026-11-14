"""Sticky UNKNOWN and private audited reconciliation on disposable PostgreSQL only."""
import os
from datetime import timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from backend.app.db import SessionLocal
from backend.app.seed import seed
from backend.app import models as M
from backend.app.models_assistant import AssistantRun
from backend.app.assistant_admission import admission_busy
from backend.app.assistant_reconciliation import admission_status,reconcile_unknown_inference,ACKNOWLEDGEMENT
from backend.app.assistant_core import run_dto
from backend.app.common import utcnow,uid
from backend.tests.test_assistant_pg import actor,fixture_run,dispatch,provider,reconcile_fixture,login

assert os.getenv('HIS_TEST_DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL')

@pytest.fixture(scope='module',autouse=True)
def seeded():
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])

def unknown(kind,state):
    a,rid,_,_,_=fixture_run()
    with SessionLocal.begin() as db:
        run=db.get(AssistantRun,rid)
        if kind=='legacy':
            # This unused queue record is terminal with known no dispatch.
            run.execution_state='failed';run.error='FIXTURE_NOT_DISPATCHED'
            run=M.InferenceRun(id=uid(),actor_id=a.user_id,task_id='task-patient-001',provider='offline_quarantine_fixture',outcome=state,reason='FIXTURE_ORIGINAL_ERROR',elapsed_ms=0,created_at=utcnow()-timedelta(days=2),context_snapshot={'lease_seconds':1},provenance={})
            db.add(run);db.flush();rid=run.id
            reason='PROVIDER_CONNECTION_FAILED'
            run.provenance={'provider_outcome':'timeout' if state=='timeout' else 'failed','provider_reason':reason}
        else:
            run.execution_state=state;run.error='FIXTURE_ORIGINAL_ERROR'
            run.lease_id=uid();run.started_at=utcnow()-timedelta(days=2);run.lease_expires_at=utcnow()-timedelta(days=1);run.hold_until=utcnow()-timedelta(days=1)
            run.provider={'provider_outcome':'timeout' if state=='timeout' else 'failed','provider_reason':'ASSISTANT_PROVIDER_CONNECTION_FAILED'}
        db.flush()
    return a,rid

@pytest.mark.parametrize('kind',['assistant','legacy'])
@pytest.mark.parametrize('state',['timeout','interrupted','running','stale_context','failed'])
def test_unknown_remains_busy_year_after_lease_and_only_audited_operator_marker_clears(kind,state):
    a,rid=unknown(kind,state)
    model=AssistantRun if kind=='assistant' else M.InferenceRun
    with SessionLocal.begin() as db:
        run=db.get(model,rid);original=run.error if kind=='assistant' else run.reason
        assert admission_busy(db,now=utcnow()+timedelta(days=366))
        assert admission_status(db,run,kind)['state']=='quarantined'
        forged={'operator_reconciliation':{'version':1,'run_id':rid,'audit_event_id':uid(),'acknowledgement':ACKNOWLEDGEMENT}}
        if kind=='assistant':run.provider={**run.provider,**forged}
        else:run.provenance={**run.provenance,**forged}
        db.flush();assert admission_busy(db,now=utcnow()+timedelta(days=366))
        marker=reconcile_fixture(db,kind,rid)
        assert not admission_busy(db,now=utcnow()+timedelta(days=366))
        assert (run.error if kind=='assistant' else run.reason)==original
        data=run.provider if kind=='assistant' else run.provenance
        assert data['provider_reason'] in ('ASSISTANT_PROVIDER_CONNECTION_FAILED','PROVIDER_CONNECTION_FAILED')
        audit=db.get(M.AuditEvent,marker['audit_event_id'])
        assert audit.action=='inference_unknown_reconciled' and audit.actor_id=='user-system_admin'
        assert admission_status(db,run,kind)['reconciliation']==marker
        if kind=='assistant':assert run_dto(db,a,run)['admission']['reason']=='OPERATOR_RECONCILED'

def test_private_reconciliation_requires_authority_exact_ack_and_drain_evidence():
    a,rid=unknown('assistant','timeout')
    with SessionLocal.begin() as db:
        with pytest.raises(HTTPException) as denied:
            reconcile_unknown_inference(db,a,kind='assistant',run_id=rid,acknowledgement=ACKNOWLEDGEMENT,evidence_reference='test',workers_quiesced=True,provider_drained=True)
        assert denied.value.status_code==403
        admin=actor(db,'system_admin')
        for patch in ({'acknowledgement':'yes'},{'evidence_reference':''},{'workers_quiesced':False},{'provider_drained':False}):
            args={'kind':'assistant','run_id':rid,'acknowledgement':ACKNOWLEDGEMENT,'evidence_reference':'offline-provider-completion-receipt','workers_quiesced':True,'provider_drained':True,**patch}
            with pytest.raises(HTTPException) as invalid:reconcile_unknown_inference(db,admin,**args)
            assert invalid.value.status_code==422
        assert admission_busy(db)
        reconcile_fixture(db,'assistant',rid)

def test_marker_and_audit_are_atomic_and_no_public_clear_route_exists():
    a,rid=unknown('assistant','timeout')
    with pytest.raises(RuntimeError):
        with SessionLocal.begin() as db:
            reconcile_fixture(db,'assistant',rid)
            raise RuntimeError('Simulated private transaction failure')
    with SessionLocal.begin() as db:
        assert admission_busy(db)
        assert not db.scalar(select(M.AuditEvent.id).where(M.AuditEvent.entity_id==rid,M.AuditEvent.action=='inference_unknown_reconciled'))
        reconcile_fixture(db,'assistant',rid)
    c=login('system_admin')
    assert c.post('/api/v2/assistant/runs/'+rid+'/reconcile',json={'acknowledgement':ACKNOWLEDGEMENT}).status_code in (404,405)
    from backend.app.main import app
    assert not any(path.endswith('/reconcile') for path in app.openapi()['paths'])

@pytest.mark.parametrize('outcome',['success','abstained','invalid_output','failed'])
def test_only_positive_verified_late_terminal_result_clears_interrupted_unknown(outcome):
    a,rid,_,_,_=fixture_run()
    def late(profile,locale,view):
        with SessionLocal.begin() as db:
            run=db.get(AssistantRun,rid);run.execution_state='interrupted';run.error='WORKER_LEASE_EXPIRED';run.completed_at=utcnow()
        if outcome=='success':return provider(profile,locale,view)
        return {'outcome':outcome,'reason':'OFFLINE_TEST_RESULT','artifact':None,'provenance':{'test_verified_terminal':outcome=='abstained'},'usage':None}
    assert dispatch(late)['state']=='interrupted'
    with SessionLocal.begin() as db:
        run=db.get(AssistantRun,rid)
        assert run.error=='WORKER_LEASE_EXPIRED'
        if outcome in ('success','abstained'):
            assert not admission_busy(db)
            assert admission_status(db,run,'assistant')['reason']=='VERIFIED_PROVIDER_TERMINAL'
            marker=run.provider['positive_terminal_evidence']
            assert db.get(M.AuditEvent,marker['audit_event_id']).action=='inference_provider_terminal_observed'
        else:
            assert admission_busy(db,now=utcnow()+timedelta(days=366))
            assert 'positive_terminal_evidence' not in run.provider
            reconcile_fixture(db,'assistant',rid)

def test_normal_success_releases_shared_admission_and_has_audited_terminal_evidence():
    a,rid,_,_,_=fixture_run()
    assert dispatch()['state']=='succeeded'
    with SessionLocal() as db:
        assert not admission_busy(db)
        run=db.get(AssistantRun,rid);marker=run.provider['positive_terminal_evidence']
        assert marker['outcome']=='success' and db.get(M.AuditEvent,marker['audit_event_id'])

@pytest.mark.parametrize('outcome',['success','abstained','invalid_output','failed'])
def test_legacy_late_positive_terminal_can_clear_interrupted_but_generic_failure_cannot(outcome):
    from backend.app import ai
    from backend.tests.test_assistant_pg import context
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);a=actor(db)
        task=M.Task(id=uid(),organization_id=a.organization_id,facility_id=a.facility_id,patient_id=pid,encounter_id=eid,domain='D37',kind='document_review',title='Synthetic terminal observation')
        db.add(task);db.flush();tid=task.id
    key=uid()
    class LegacyProvider:
        name='offline_sticky_legacy';is_live=True;timeout_seconds=2
        def public_config(self):return {'test_double':True}
        def generate_document(self,*args):
            with SessionLocal.begin() as db:
                run=db.scalar(select(M.InferenceRun).where(M.InferenceRun.operation_key==key))
                run.outcome='interrupted';run.reason='WORKER_LEASE_EXPIRED';run.completed_at=utcnow()
            return {'outcome':outcome,'reason':'OFFLINE_TEST_RESULT','action':{'text':'Synthetic reviewed draft','completeness':{}} if outcome=='success' else None,'provenance':{'test_verified_terminal':outcome in ('success','abstained')},'usage':None}
    with SessionLocal() as db:
        doc=db.get(M.Document,did);task=db.get(M.Task,tid);visit=db.get(M.Encounter,eid);revision=db.get(M.DocumentVersion,doc.current_version_id)
        body=ai.Propose(task_id=tid,document_id=did)
        result=ai.live_propose(db,a,body,key,body.model_dump(),LegacyProvider(),task,doc,visit,revision)
        assert result['run']['outcome']=='interrupted' and result['proposal'] is None
        db.commit()  # Mirrors get_db's API dependency commit on this early-return path.
    with SessionLocal.begin() as db:
        run=db.scalar(select(M.InferenceRun).where(M.InferenceRun.operation_key==key))
        assert run.reason=='WORKER_LEASE_EXPIRED'
        if outcome in ('success','abstained'):
            assert not admission_busy(db)
            assert admission_status(db,run,'legacy')['reason']=='VERIFIED_PROVIDER_TERMINAL'
        else:
            assert admission_busy(db,now=utcnow()+timedelta(days=366))
            reconcile_fixture(db,'legacy',run.id)
