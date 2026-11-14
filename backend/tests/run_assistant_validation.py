"""Run through scripts/test_with_postgres.py; preserves historical core evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

assert os.getenv('HIS_TEST_DATABASE_URL')==os.getenv('DATABASE_URL') and os.getenv('HIS_TEST_DATABASE_URL'), 'Disposable PostgreSQL wrapper required'
ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT)
OUT=ROOT/'evidence/ai-driven-backend'
OUT.mkdir(parents=True,exist_ok=True)
historical=ROOT/'evidence/fullsystem/core-journeys.json'
before=historical.read_bytes() if historical.exists() else None
commands=[
    [sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],
    [sys.executable,'-m','alembic','-c','backend/alembic.ini','check'],
    [sys.executable,'-m','pytest','backend/tests/test_assistant_pg.py','backend/tests/test_core.py','backend/tests/test_document_provider_unit.py','-q','--junitxml=evidence/ai-driven-backend/pytest-results.xml'],
]
report={'status':'RUNNING','scope':'disposable PostgreSQL18 + FastAPI + explicit offline provider doubles; no live inference/server/deployment','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'source_sha256':{str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT/'backend').rglob('*.py'))}}
code=1
try:
    for command in commands:
        completed=subprocess.run(command)
        report['commands'].append({'command':command,'exit_code':completed.returncode})
        code=completed.returncode
        if code:break
    if historical.exists() and historical.read_bytes()!=before:
        (OUT/'executed-core-journeys.json').write_bytes(historical.read_bytes())
finally:
    if before is not None:historical.write_bytes(before)
    elif historical.exists():historical.unlink()
    report['status']='PASS' if code==0 else 'FAIL'
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    (OUT/'execution.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
sys.exit(code)
