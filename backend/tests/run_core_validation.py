"""Migration, explicit seed, schema drift and core acceptance on disposable PostgreSQL."""
import os,subprocess,sys,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT)
EVIDENCE=ROOT/'evidence/fullsystem';EVIDENCE.mkdir(parents=True,exist_ok=True)
(EVIDENCE/'core-journeys.json').unlink(missing_ok=True)
commands=[
 [sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],
 [sys.executable,'-m','backend.app.seed'],
 [sys.executable,'-m','alembic','-c','backend/alembic.ini','check'],
 [sys.executable,'-m','pytest','backend/tests/test_core.py','-q'],
]
report={'started_at':datetime.now(timezone.utc).isoformat(),'scope':'actual PostgreSQL + FastAPI TestClient; not browser','commands':[],'status':'RUNNING'}
report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'backend').rglob('*.py'))}
exit_code=0
for command in commands:
    result=subprocess.run(command)
    report['commands'].append({'command':command,'exit_code':result.returncode})
    if result.returncode:
        exit_code=result.returncode;break
report['status']='PASS' if exit_code==0 else 'FAIL'
report['finished_at']=datetime.now(timezone.utc).isoformat()
(EVIDENCE/'core-execution.json').write_text(json.dumps(report,indent=2))
sys.exit(exit_code)
