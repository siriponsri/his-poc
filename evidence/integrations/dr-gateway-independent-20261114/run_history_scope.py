import os,json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('C:/Users/User/Desktop/myProject/his-poc');OUT=Path(__file__).parent
names=json.loads((OUT/'final-source-before.json').read_text())
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
assert before==names,'Frozen runtime no longer matches independently qualified source'
python=str(ROOT/'.venv/Scripts/python.exe')
command=[python,'-B','scripts/test_with_postgres.py','--pg-bin','C:/Users/User/.cache/his-poc-tools/pg18/pgsql/bin','--',python,'-B','scripts/run_pg_suite.py',str(OUT/'history_scope_proof.py'),'-q','-s','-p','no:cacheprovider','--junitxml='+str(OUT/'history-scope.xml')]
started=datetime.now(timezone.utc).isoformat()
with (OUT/'history-scope.txt').open('w',encoding='utf-8') as output:
    result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'},stdout=output,stderr=subprocess.STDOUT)
after={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
record={'status':'PASS' if result.returncode==0 and before==after else 'FAIL','exit_code':result.returncode,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'command':command,'source_before':before,'source_after':after,'source_drift':[n for n in names if before[n]!=after[n]],'limits':['Disposable PostgreSQL+HIS TestClient only; no external receiver/model/browser/deployment']}
(OUT/'history-scope.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ('status','exit_code','source_drift')}))
if result.returncode:print((OUT/'history-scope.txt').read_text()[-6000:])
raise SystemExit(record['status']!='PASS')
