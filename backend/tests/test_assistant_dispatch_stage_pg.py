"""Real adapter -> persisted admission tests, entirely offline HTTP MockTransport."""
import os
from datetime import timedelta
import httpx
import pytest
from sqlalchemy import select,func
from backend.app.db import SessionLocal
from backend.app.seed import seed
from backend.app import models as M,ai
from backend.app.models_assistant import AssistantRun,AssistantRevision
from backend.app.assistant_core import enqueue
from backend.app.assistant_worker import run_once
from backend.app.assistant_reconciliation import admission_status
from backend.app.assistant_admission import admission_busy
from backend.app.assistant_provider import AssistantOllamaProvider,MODEL,MODEL_DIGEST
from backend.app.assistant_schema import validate_assistant_artifact
from backend.app.providers import DrTrainOllamaProvider,OllamaSettings
from backend.app.common import uid,utcnow
from backend.tests.test_assistant_pg import context,actor,CONFIG,dispatch,reconcile_fixture

assert os.getenv('HIS_TEST_DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL')

@pytest.fixture(scope='module',autouse=True)
def seeded():
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])

def adapter(kind,mode):
    calls=[]
    def handle(request):
        calls.append(request.url.path)
        if request.url.path=='/api/version':return httpx.Response(200,json={'version':'0.0.0' if mode=='post_identity_fail' and '/api/chat' in calls else '0.12.6'})
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':MODEL,'digest':MODEL_DIGEST,'details':{}}]})
        if request.url.path=='/api/show':return httpx.Response(200,json={'template':'offline-stage-test-template','parameters':'','capabilities':[] if mode=='pre_show_invalid' else ['completion']})
        assert request.url.path=='/api/chat'
        if mode=='dropped':raise httpx.ReadError('Offline drop after dispatch',request=request)
        if mode=='chat_http_error':return httpx.Response(500,json={'error':'offline injected HTTP failure'})
        if mode=='malformed_json':return httpx.Response(200,content=b'{',headers={'content-type':'application/json'})
        if mode=='non_json':return httpx.Response(200,content=b'not json',headers={'content-type':'text/plain'})
        if mode=='non_object':return httpx.Response(200,json=[])
        if mode=='oversized':return httpx.Response(200,content=b'x'*262145)
        return httpx.Response(200,json={'model':'wrong-model' if mode=='terminal_wrong_model' else MODEL,'done':True,'done_reason':'stop','message':{'role':'assistant','content':'{}'},'prompt_eval_count':10,'eval_count':2})
    settings=OllamaSettings('http://127.0.0.1:11435',MODEL,MODEL_DIGEST,'0.12.6',timeout_seconds=5,context_tokens=4096 if kind=='assistant' else 8192,max_output_tokens=512 if kind=='assistant' else 1024)
    cls=AssistantOllamaProvider if kind=='assistant' else DrTrainOllamaProvider
    return cls(settings,transport=httpx.MockTransport(handle)),calls

def exercise(kind,mode):
    p,calls=adapter(kind,mode)
    with SessionLocal.begin() as db:
        pid,eid,did=context(db);second_pid,second_eid,_=context(db);a=actor(db)
        if kind=='assistant':first,_=enqueue(db,a,'visit_preparation',pid,eid,'en',uid());rid=first.id
        else:
            task=M.Task(id=uid(),organization_id=a.organization_id,facility_id=a.facility_id,patient_id=pid,encounter_id=eid,domain='D37',kind='document_review',title='Offline actual-adapter stage test')
            db.add(task);db.flush();tid=task.id
        queued,_=enqueue(db,a,'visit_preparation',second_pid,second_eid,'en',uid());queued_id=queued.id
    if kind=='assistant':
        result=run_once(prepare=p.prepare,validate=validate_assistant_artifact,config=lambda:CONFIG)
        assert result['run_id']==rid
    else:
        key=uid()
        with SessionLocal() as db:
            doc=db.get(M.Document,did);task=db.get(M.Task,tid);visit=db.get(M.Encounter,eid);revision=db.get(M.DocumentVersion,doc.current_version_id)
            body=ai.Propose(task_id=tid,document_id=did)
            result=ai.live_propose(db,a,body,key,body.model_dump(),p,task,doc,visit,revision)
            assert result['proposal'] is None
            rid=result['run']['id'];db.commit()
    return p,calls,rid,queued_id

MODES=['malformed_json','non_json','non_object','oversized','dropped','chat_http_error','terminal_wrong_model','terminal_bad_artifact','post_identity_fail','pre_show_invalid']

@pytest.mark.parametrize('kind',['assistant','legacy'])
@pytest.mark.parametrize('mode',MODES)
def test_real_adapter_stage_controls_physical_admission_without_accepting_bad_clinical_output(kind,mode,monkeypatch):
    monkeypatch.delenv('HIS_ASSISTANT_TEMPLATE_SHA256',raising=False)
    p,calls,rid,queued_id=exercise(kind,mode)
    physical_clear=mode in ('terminal_bad_artifact','post_identity_fail','pre_show_invalid')
    expected_chat=0 if mode=='pre_show_invalid' else 1
    assert calls.count('/api/chat')==expected_chat
    with SessionLocal.begin() as db:
        run=db.get(AssistantRun if kind=='assistant' else M.InferenceRun,rid)
        data=run.provider if kind=='assistant' else run.provenance
        observed=data['provenance'] if kind=='assistant' else data
        assert observed['dispatch_started'] is (mode!='pre_show_invalid')
        assert observed['terminal_response_observed'] is (mode in ('terminal_bad_artifact','post_identity_fail'))
        assert (run.execution_state if kind=='assistant' else run.outcome) in ('failed','invalid_output')
        status=admission_status(db,run,kind,now=utcnow()+timedelta(days=366))
        assert (status['state']=='clear') is physical_clear
        if mode=='pre_show_invalid':
            marker=data['no_dispatch_evidence'];assert status['reason']=='VERIFIED_NO_DISPATCH'
        elif physical_clear:
            marker=data['positive_terminal_evidence'];assert status['reason']=='VERIFIED_PROVIDER_TERMINAL'
            assert len(marker['response_sha256'])==64
        else:marker=None
        if marker:assert db.get(M.AuditEvent,marker['audit_event_id'])
        if kind=='assistant':assert not db.scalar(select(AssistantRevision.id).where(AssistantRevision.run_id==rid))
        else:assert not db.scalar(select(M.Proposal.id).where(M.Proposal.run_id==rid))
    if not physical_clear:
        assert run_once(prepare=p.prepare if kind=='assistant' else lambda *_:pytest.fail('Must not dispatch'),validate=validate_assistant_artifact,config=lambda:CONFIG)['dispatched']==0
        assert calls.count('/api/chat')==expected_chat
        with SessionLocal.begin() as db:
            assert admission_busy(db,now=utcnow()+timedelta(days=366))
            reconcile_fixture(db,kind,rid)
    assert dispatch()['run_id']==queued_id

@pytest.mark.parametrize('kind',['assistant','legacy'])
def test_raw_false_false_or_terminal_flags_cannot_forge_audited_clear(kind,monkeypatch):
    monkeypatch.delenv('HIS_ASSISTANT_TEMPLATE_SHA256',raising=False)
    p,calls,rid,queued_id=exercise(kind,'malformed_json')
    with SessionLocal.begin() as db:
        run=db.get(AssistantRun if kind=='assistant' else M.InferenceRun,rid)
        for flags in ({'dispatch_started':False,'terminal_response_observed':False},{'dispatch_started':True,'terminal_response_observed':True,'response_sha256':'a'*64}):
            if kind=='assistant':run.provider={**run.provider,'provenance':{**run.provider['provenance'],**flags}}
            else:run.provenance={**run.provenance,**flags}
            db.flush();assert admission_status(db,run,kind)['state']=='quarantined'
            assert admission_busy(db,now=utcnow()+timedelta(days=366))
        reconcile_fixture(db,kind,rid)
    assert dispatch()['run_id']==queued_id
