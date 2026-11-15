"""Actual collector/schema/provider integration with an explicitly offline HTTP transport."""
import json
import os
from pathlib import Path
import pytest
from sqlalchemy import select
from backend.app.db import SessionLocal
from backend.app.seed import seed
from backend.app.assistant_collectors import collect_packet
from backend.app.assistant_core import enqueue
from backend.app.assistant_worker import run_once
from backend.app.models_assistant import AssistantRun, AssistantRevision
from backend.app.assistant_provider import SYSTEM_PROMPT, PROFILE_PROMPTS, TEMPLATE_RESERVE, _validate_input
from backend.app.assistant_schema import validate_assistant_artifact
from backend.app.common import uid
from backend.tests.test_assistant_pg import context, actor, CONFIG
from backend.tests.test_assistant_provider import provider, responder

assert os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL')

@pytest.fixture(scope='module',autouse=True)
def seeded():
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])

ROWS=[]

@pytest.mark.parametrize('role,profile',[
    ('clinician','visit_preparation'),('nurse','nursing_handover'),('registration','records_readiness'),('laboratory','laboratory_handoff')])
def test_actual_pg_collector_provider_schema_worker_and_complete_prompt_budget(role,profile,monkeypatch):
    monkeypatch.delenv('HIS_ASSISTANT_TEMPLATE_SHA256',raising=False)
    with SessionLocal.begin() as db:
        pid,eid,_=context(db);a=actor(db,role)
        packet=collect_packet(db,a,profile,pid,eid,'th');view=packet['view']
        run,_=enqueue(db,a,profile,pid,eid,'th',uid());rid=run.id
    # This is the real provider envelope and complete system/profile/locale text.
    envelope=_validate_input(profile,'th',view)
    system=SYSTEM_PROMPT+' '+PROFILE_PROMPTS[profile]+' Write Thai.'
    full_input_bytes=len((system+envelope).encode('utf-8'))
    assert len(envelope.encode('utf-8'))<=2000
    assert full_input_bytes+TEMPLATE_RESERVE+512<=4096
    assert len((SYSTEM_PROMPT+' '+PROFILE_PROMPTS[profile]+' Write English.').encode('utf-8'))<=1328
    first=next((source for source in view['sources'] if source.get('text')),None)
    if first:facts=[{'source_ref':first['ref'],'quote':first['text'][:80]}]
    else:
        first=next((source for source in view['sources'] if source['kind']=='lab'),view['sources'][0]);field='result' if first['kind']=='lab' else next(key for key,value in first['fields'].items() if isinstance(value,str))
        facts=[{'source_ref':first['ref'],'field':field}]
    drafts=[]
    for candidate in view['effect_candidates']:
        if candidate.get('draft_id'):
            note=next((source for source in view['sources'] if source.get('text')),None)
            source=note or view['sources'][0]
            drafts.append({'id':candidate['draft_id'],'title':'Prepared draft','text':source.get('text') or next(str(value) for value in source['fields'].values() if isinstance(value,str)),'source_refs':[source['ref']]})
    artifact={'facts':facts,'work_gaps':[],'drafts':drafts,'suggested_effects':view['effect_candidates'],'requires_review':True}
    verified=validate_assistant_artifact(profile,artifact,view)
    handler,calls=responder(artifact)
    adapter=provider(handler)
    result=run_once(prepare=adapter.prepare,validate=validate_assistant_artifact,config=lambda:CONFIG)
    assert result=={'dispatched':1,'run_id':rid,'state':'succeeded'}
    assert calls.count(('POST','/api/chat'))==1
    with SessionLocal() as db:
        run=db.get(AssistantRun,rid)
        revision=db.scalar(select(AssistantRevision).where(AssistantRevision.run_id==rid))
        assert revision.artifact==verified
        assert run.provider['provenance']['model_digest']==adapter.settings.model_digest
        assert run.review_state=='pending' and run.measured_cost is None
    ROWS.append({'profile':profile,'canonical_view_bytes':len(envelope.encode('utf-8')),'complete_input_bytes':full_input_bytes,'template_reserve':TEMPLATE_RESERVE,'max_output_tokens':512,'context_tokens':4096,'mock_transport_chat_calls':1,'worker_state':'succeeded','schema_validation':'PASS','live_network_calls':0})
    out=Path('evidence/ai-driven-backend/provider-integration.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'scope':'actual PostgreSQL18 collector + actual provider/schema + explicit offline HTTP MockTransport; NOT real model qualification','profiles':ROWS},indent=2),encoding='utf-8')

def test_more_than_twelve_sources_are_explicitly_omitted_with_all_manifest_evidence_kept():
    from backend.app.models import Document
    with SessionLocal.begin() as db:
        pid,eid,_=context(db);a=actor(db,'registration')
        for _ in range(24):
            db.add(Document(id=uid(),organization_id=a.organization_id,facility_id=a.facility_id,patient_id=pid,encounter_id=eid,title='X',status='draft'))
        db.flush()
        packet=collect_packet(db,a,'records_readiness',pid,eid)
        view=packet['view']
        assert len(view['sources'])<=12
        assert all(len(c['source_refs'])<=12 for c in view['effect_candidates'])
        assert view['coverage']['eligible_sources']==len(packet['manifest']['sources'])
        assert view['coverage']['omitted_sources']>=15
        assert view['coverage']['included_sources']+view['coverage']['omitted_sources']==view['coverage']['eligible_sources']
