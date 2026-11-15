"""Qualify 0005->0006 preservation only in the disposable PostgreSQL wrapper."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
assert os.environ.get('HIS_TEST_DATABASE_URL')==os.environ.get('DATABASE_URL') and os.environ.get('HIS_TEST_DATABASE_URL'),'Disposable PostgreSQL wrapper required'
assert 'his_test@127.0.0.1:' in os.environ['DATABASE_URL'],'Only the wrapper loopback database is accepted'
OUT=ROOT/'var/ai-team-tests';OUT.mkdir(exist_ok=True)


def command(*args,expected=0):
    result=subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini',*args],capture_output=True)
    assert result.returncode==expected,(args,result.stderr.decode(errors='replace')[-1000:])
    return result


def snapshot(db):
    tables=[row[0] for row in db.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
    values={}
    for name in tables:
        assert name.replace('_','').isalnum()
        if name=='alembic_version':continue
        rows=sorted(row[0] for row in db.execute('SELECT row_to_json(r)::text FROM "'+name+'" r'))
        values[name]={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}
    return values


command('upgrade','0005_assistant_workspaces')
import psycopg
from backend.app.db import SessionLocal
from backend.app.seed import seed
with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])
url=os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)
with psycopg.connect(url) as db:
    db.execute('SET TRANSACTION READ ONLY');before=snapshot(db)
assert 'task_coordination' not in before
files=Path(os.environ['FILE_STORAGE_ROOT'])
before_files={p.relative_to(files).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files.rglob('*') if p.is_file()}
command('upgrade','head')
command('check')
with psycopg.connect(url) as db:
    db.execute('SET TRANSACTION READ ONLY');after=snapshot(db)
    assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0006_team_coordination'
assert after['task_coordination']['rows']==0 and set(after)-set(before)=={'task_coordination'}
assert all(after[name]==value for name,value in before.items())
from fastapi.testclient import TestClient
from backend.app.main import app
assert TestClient(app).get('/ready').json()=={'ready':True,'migration':'0006_team_coordination'}
# The explicit downgrade guard must fail without changing schema or data.
blocked=subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','downgrade','-1'],capture_output=True)
assert blocked.returncode!=0 and b'No destructive downgrade' in blocked.stderr
with psycopg.connect(url) as db:
    db.execute('SET TRANSACTION READ ONLY');assert snapshot(db)==after
    assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0006_team_coordination'
after_files={p.relative_to(files).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files.rglob('*') if p.is_file()}
assert after_files==before_files
report={'status':'PASS_DISPOSABLE_0005_TO_0006_SCHEMA_AND_ROW_PRESERVATION','old_tables_preserved':len(before),'new_empty_tables':['task_coordination'],'old_row_hashes':before,'file_count':len(before_files),'files_preserved':True,'alembic_metadata_check':'PASS','candidate_ready_http':200,'destructive_downgrade_guard':'PASS_BLOCKED_WITH_NO_CHANGES','production_database_used':False,'model_calls':0,'production_rollback':'NOT_RUN'}
(OUT/'schema-preservation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='old_row_hashes'}))
