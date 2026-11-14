"""Export authorized synthetic source packets from a disposable PostgreSQL fixture.

Input preparation only. This script never imports a generation function or makes
model/server requests. Run through scripts/test_with_postgres.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
assert os.getenv('HIS_TEST_DATABASE_URL') and os.environ['HIS_TEST_DATABASE_URL']==os.getenv('DATABASE_URL'), 'Disposable PostgreSQL wrapper required'
from backend.app.db import SessionLocal, engine
from backend.app.seed import seed
from backend.app.core import create_document, DocumentInput
from backend.app.assistant_collectors import collect_packet
from backend.app.assistant_provider import SYSTEM_PROMPT, PROFILE_PROMPTS, TEMPLATE_RESERVE
from backend.app.common import authorization_hash, canonical, digest, uid
from backend.tests.test_assistant_pg import context, actor

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    assert engine.url.database=='his_test'
    assert not args.output.exists(), 'Preserve an existing qualification packet export; choose a new output path'
    subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],check=True)
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])
    output={'schema':'carebalance-assistant-input-qualification-v1','data_class':'AUTHORED_SYNTHETIC','source_environment':'isolated_disposable_postgresql18','created_at':datetime.now(timezone.utc).isoformat(),'live_model_calls':0,'production_database_queries':0,'packets':[]}
    for role,profile in [('clinician','visit_preparation'),('nurse','nursing_handover'),('registration','records_readiness'),('laboratory','laboratory_handoff')]:
        with SessionLocal.begin() as db:
            pid,eid,_=context(db);staff=actor(db,role)
            if role in ('clinician','nurse'):
                note='มาตามนัด รอทบทวนยาและประวัติแพ้ยา BP 138/84 mmHg ชีพจร 78 ครั้ง/นาที'
                create_document(DocumentInput(patient_id=pid,encounter_id=eid,title='บันทึกติดตามสังเคราะห์',content=note),staff,db,'qualification-source:'+uid())
            packet=collect_packet(db,staff,profile,pid,eid,'th')
            view=packet['view'];view_bytes=len(canonical(view).encode('utf-8'))
            full_bytes=len((SYSTEM_PROMPT+' '+PROFILE_PROMPTS[profile]+' Write Thai.'+canonical(view)).encode('utf-8'))
            assert view_bytes<=2000 and full_bytes+TEMPLATE_RESERVE+1024<=4096
            record={'profile':profile,'locale':'th','data_class':'AUTHORED_SYNTHETIC','actor':{'user_id':staff.user_id,'username':staff.username,'roles':sorted(staff.roles),'permissions':sorted(staff.permissions),'organization_id':staff.organization_id,'facility_id':staff.facility_id,'authorization_hash':authorization_hash(staff)},'patient_id':pid,'encounter_id':eid,'source_digest':packet['source_digest'],'input_hash':packet['input_hash'],'coverage':view['coverage'],'manifest':packet['manifest'],'inference_view':view,'canonical_view_bytes':view_bytes,'complete_input_bytes':full_bytes,'model_context_tokens':4096,'max_output_tokens':1024,'template_reserve':TEMPLATE_RESERVE}
            record['packet_sha256']=digest(record)
            output['packets'].append(record)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    args.output.write_bytes(raw)
    receipt={'artifact':args.output.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'data_class':'AUTHORED_SYNTHETIC','live_model_calls':0,'production_database_queries':0,'profiles':[{'profile':p['profile'],'input_hash':p['input_hash'],'source_digest':p['source_digest'],'packet_sha256':p['packet_sha256'],'canonical_view_bytes':p['canonical_view_bytes'],'complete_input_bytes':p['complete_input_bytes'],'coverage':p['coverage']} for p in output['packets']],'source_sha256':{name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ['backend/app/assistant_collectors.py','backend/app/assistant_provider.py','backend/app/assistant_schema.py','backend/tests/export_assistant_qualification_packets.py']}}
    receipt_path=args.output.with_name(args.output.stem+'.sha256.json')
    assert not receipt_path.exists(), 'Preserve existing export receipt'
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','artifact':str(args.output),'receipt':str(receipt_path),'sha256':receipt['sha256'],'profiles':[{'profile':p['profile'],'view_bytes':p['canonical_view_bytes'],'complete_input_bytes':p['complete_input_bytes']} for p in output['packets']],'live_model_calls':0,'production_database_queries':0}))

if __name__=='__main__':main()
