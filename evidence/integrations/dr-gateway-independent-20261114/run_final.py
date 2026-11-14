import os,sys,json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('C:/Users/User/Desktop/myProject/his-poc');OUT=Path(__file__).parent
names=['backend/app/dr_client.py','backend/app/dr_core.py','backend/app/dr_gateway.py','backend/app/dr_protocol.py','backend/app/models_dr.py','backend/app/main.py','backend/app/model_registry.py','backend/migrations/versions/0004_dr_screening_bridge.py','backend/tests/test_dr_client_unit.py','backend/tests/test_dr_gateway_pg.py','backend/tests/test_dr_receiver_http_pg.py']
protected=['backend/app/auth.py','backend/app/ai.py','backend/app/integrations.py','backend/app/integration_clients.py','backend/app/models_integrations.py','backend/migrations/versions/0003_carebalance_integrations.py','backend/app/domains/clinical.py','backend/app/domains/erp.py']
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names+protected}
assert before['backend/app/dr_client.py']=='333654ca5625a762ae670514b82c481087d62cdb2b2fcded9e6b85f96fffeb0c'
assert before['backend/app/dr_gateway.py']=='674b6e9815729a420e7cc3e351f0b32156af1c5de47134a0e9b04deafe08cb29'
(OUT/'final-source-before.json').write_text(json.dumps(before,indent=2)+'\n')
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
python=str(ROOT/'.venv/Scripts/python.exe')
prefix=[python,'-B','scripts/test_with_postgres.py','--pg-bin','C:/Users/User/.cache/his-poc-tools/pg18/pgsql/bin','--',python,'-B','scripts/run_pg_suite.py']
checks=[('final-qualified-suites',prefix+['backend/tests/test_dr_client_unit.py','backend/tests/test_dr_gateway_pg.py','backend/tests/test_dr_receiver_http_pg.py','-q','-p','no:cacheprovider','--junitxml='+str(OUT/'final-qualified-suites.xml')]),
        ('final-independent-negatives',prefix+[str(OUT/'fixed_proof.py'),'-q','-s','-p','no:cacheprovider','--junitxml='+str(OUT/'final-independent-negatives.xml')])]
results=[]
for label,command in checks:
    start=datetime.now(timezone.utc).isoformat();print('Starting '+label,flush=True)
    with (OUT/(label+'.txt')).open('w',encoding='utf-8') as f:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    results.append({'name':label,'command':command,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':result.returncode})
    print(label,result.returncode,flush=True)
    if result.returncode:print((OUT/(label+'.txt')).read_text(encoding='utf-8')[-5000:])
after={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names+protected}
record={'at':datetime.now(timezone.utc).isoformat(),'status':'PASS' if all(r['exit_code']==0 for r in results) and before==after else 'FAIL',
        'results':results,'source_before':before,'source_after':after,'source_drift':[n for n in before if before[n]!=after[n]],
        'protected_files':protected,'limits':['Fresh disposable local PostgreSQL; qualified-suite includes actual two-process HTTP receiver flow','Independent adversarial tests use actual HIS/PostgreSQL and signed MockTransport malformed receipts, never a real clinical/model result','No repository/Git/config/env/deployment/browser/original-DR state mutation by reviewer']}
(OUT/'final-review.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':record['status'],'results':[{k:r[k] for k in ('name','exit_code')} for r in results],'source_drift':record['source_drift'],'evidence':str(OUT)}))
raise SystemExit(record['status']!='PASS')
