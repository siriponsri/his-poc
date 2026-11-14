import os,sys,json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('C:/Users/User/Desktop/myProject/his-poc');OUT=Path(__file__).parent
names=['backend/app/dr_client.py','backend/app/dr_core.py','backend/app/dr_gateway.py','backend/app/dr_protocol.py','backend/app/models_dr.py','backend/app/main.py','backend/app/model_registry.py','backend/migrations/versions/0004_dr_screening_bridge.py']
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
(OUT/'pre-fix-source.json').write_text(json.dumps(before,indent=2)+'\n')
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','scripts/test_with_postgres.py','--pg-bin','C:/Users/User/.cache/his-poc-tools/pg18/pgsql/bin','--',str(ROOT/'.venv/Scripts/python.exe'),'-B','scripts/run_pg_suite.py',str(OUT/'pre_fix_proof.py'),'-q','-s','-p','no:cacheprovider','--junitxml='+str(OUT/'pre-fix-proof.xml')]
with (OUT/'pre-fix-proof.txt').open('w',encoding='utf-8') as f:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
after={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
(OUT/'pre-fix-result.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':result.returncode,'source_before':before,'source_after':after,'source_drift':[n for n in names if before[n]!=after[n]],'scope':'Independent source sender-boundary/lease/grant observations; actual disposable PG with signed MockTransport, no real receiver/browser/model'},indent=2)+'\n')
print(json.dumps({'exit_code':result.returncode,'source_drift':[n for n in names if before[n]!=after[n]],'log':str(OUT/'pre-fix-proof.txt')}))
print((OUT/'pre-fix-proof.txt').read_text(encoding='utf-8')[-4500:])
raise SystemExit(result.returncode)
