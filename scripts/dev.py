"""Portable explicit initialize/migrate/seed/start launcher. Never deletes volumes."""
from __future__ import annotations
import argparse, os, pathlib, secrets, shutil, subprocess, sys, time, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(args, *, env=None, capture=False):
    return subprocess.run(args, cwd=ROOT, env=env, check=True,
        stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None,
        text=True)

def load_env():
    out = dict(os.environ)
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1); out.setdefault(k.strip(),v.strip())
    return out

def initialize():
    p=ROOT/'.env'
    if p.exists():
        print('.env already exists; retained without changes.');return
    password=secrets.token_urlsafe(24)
    content='POSTGRES_PASSWORD='+secrets.token_hex(24)+'\nHIS_SEED_PASSWORD='+password+'\nHIS_WEB_PORT=8000\nHIS_PLATFORM_OPERATORS=user-operations_admin\n'
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(content)
    print('Created private .env. Read HIS_SEED_PASSWORD locally for synthetic account login; do not share this file.')

def docker_preflight(env):
    if not shutil.which('docker'):raise RuntimeError('Docker executable is unavailable. Install/start Docker Desktop with Linux containers, or choose native-up with PostgreSQL 18 and DATABASE_URL.')
    try:
        run(['docker','info'],env=env,capture=True)
        run(['docker','compose','version'],env=env,capture=True)
    except subprocess.CalledProcessError:
        raise RuntimeError('Docker engine or Compose is unavailable. Start Docker Desktop, wait for Linux engine readiness, and retry. No database was changed.') from None
    for key in ['POSTGRES_PASSWORD','HIS_SEED_PASSWORD']:
        if not env.get(key) or env[key].startswith('CHANGE_ME'):raise RuntimeError('Missing private configuration. Run python scripts/dev.py init and configure .env.')

def wait_web(env):
    url='http://127.0.0.1:'+env.get('HIS_WEB_PORT','8000')+'/ready'
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=2) as response:
                if response.status==200:
                    print('Ready: '+url.removesuffix('/ready')+'/login');return
        except Exception:pass
        time.sleep(1)
    raise RuntimeError('Application readiness timed out after 90 seconds. Inspect python scripts/dev.py logs; data volumes were retained.')

def native(env):
    if not env.get('DATABASE_URL','').startswith('postgresql'):
        raise RuntimeError('Native mode requires a PostgreSQL DATABASE_URL. SQLite fallback is not supported.')
    run([sys.executable,'scripts/wait_db.py','--timeout','60'],env=env)
    run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],env=env)
    # Seed is an explicit separate action; native-up never seeds implicitly.
    run([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',env.get('HIS_WEB_PORT','8000')],env=env)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['init','config','up','start','stop','status','logs','seed','native-up','native-seed']);a=p.parse_args()
    if a.action=='init':initialize();return
    env=load_env()
    if a.action=='native-up':native(env);return
    if a.action=='native-seed':
        run([sys.executable,'scripts/wait_db.py','--timeout','60'],env=env)
        run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],env=env)
        run([sys.executable,'-m','backend.app.seed'],env=env);return
    docker_preflight(env)
    base=['docker','compose']
    if a.action=='config':run(base+['config','--quiet'],env=env);print('Compose configuration valid (secrets not printed).')
    elif a.action in ['up','start','seed']:
        run(base+['up','-d','--wait','--wait-timeout','90','db'],env=env)
        run(base+['build','app'],env=env)
        run(base+['run','--rm','--no-deps','app','python','-m','alembic','-c','backend/alembic.ini','upgrade','head'],env=env)
        # up is explicit first-time initialization. start is restart/upgrade without seed.
        if a.action in ['up','seed']:
            run(base+['run','--rm','--no-deps','app','python','-m','backend.app.seed'],env=env)
        if a.action!='seed':
            run(base+['up','-d','--no-deps','app'],env=env);wait_web(env)
    elif a.action=='stop':run(base+['stop'],env=env)
    elif a.action=='status':run(base+['ps'],env=env)
    elif a.action=='logs':run(base+['logs','--tail','100','app','db'],env=env)

if __name__=='__main__':
    try:main()
    except (RuntimeError,subprocess.CalledProcessError) as exc:
        # Never print child command/env, which may contain a password.
        print(str(exc) if isinstance(exc,RuntimeError) else 'Local command failed. Inspect the preceding application output; no reset was attempted.',file=sys.stderr);sys.exit(1)
