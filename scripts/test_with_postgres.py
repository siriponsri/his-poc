"""Run a command with a fresh, disposable PostgreSQL 18 cluster in this process.

Useful for CI and environments whose loopback is scoped to one command. This is
explicit synthetic testing, with loopback-only trust auth; never a deployment.
Example: python scripts/test_with_postgres.py --pg-bin /path/to/pg18/bin -- python -m unittest backend.tests.test_core
The child receives DATABASE_URL and HIS_TEST_DATABASE_URL. No active DB is used.
"""
from __future__ import annotations
import argparse,os,pathlib,socket,subprocess,tempfile,time,sys,json

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pg-bin',default=os.environ.get('PG_BIN',''));p.add_argument('--keep',action='store_true',help='Keep temporary cluster for evidence (prints directory)');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command and a.command[0]=='--' else a.command
    if not command:p.error('Supply a test command after --')
    prefix=pathlib.Path(a.pg_bin) if a.pg_bin else None
    def tool(name):return str(prefix/name) if prefix else name
    version=subprocess.check_output([tool('postgres'),'--version'],text=True).strip()
    if ' 18.' not in version:raise RuntimeError('PostgreSQL 18.x binaries are required')
    root=pathlib.Path(tempfile.mkdtemp(prefix='his-pg-tests-'));data=root/'data'
    env=dict(os.environ)
    if prefix:env['PATH']=str(prefix)+os.pathsep+env.get('PATH','')
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    log=(root/'postgres.log').open('w');proc=None
    try:
        subprocess.run([tool('initdb'),'-D',str(data),'--no-locale','--encoding=UTF8','--auth=trust','-U','his_test'],env=env,stdout=log,stderr=log,check=True)
        proc=subprocess.Popen([tool('postgres'),'-D',str(data),'-h','127.0.0.1','-p',str(port),'-k',''],env=env,stdout=log,stderr=log)
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('PostgreSQL process stopped; inspect '+str(root/'postgres.log'))
            ready=subprocess.run([tool('pg_isready'),'-h','127.0.0.1','-p',str(port),'-U','his_test'],env=env,capture_output=True)
            if ready.returncode==0:break
            time.sleep(.1)
        else:raise RuntimeError('PostgreSQL readiness timeout')
        subprocess.run([tool('createdb'),'-h','127.0.0.1','-p',str(port),'-U','his_test','his_test'],env=env,check=True)
        url=f'postgresql+psycopg://his_test@127.0.0.1:{port}/his_test'
        env.update(HIS_PLATFORM_OPERATORS=env.get('HIS_PLATFORM_OPERATORS','user-operations_admin'),DATABASE_URL=url,HIS_TEST_DATABASE_URL=url,FILE_STORAGE_ROOT=str(root/'files'),BACKUP_ROOT=str(root/'backups'),HIS_SEED_PASSWORD=env.get('HIS_SEED_PASSWORD','SyntheticTestOnly-2026!'))
        print(json.dumps({'postgres':version,'profile':'disposable_synthetic_test','database':'his_test','network':'loopback-only','files':str(root/'files')}),flush=True)
        result=subprocess.run(command,env=env).returncode
        return result
    finally:
        if proc and proc.poll() is None:
            subprocess.run([tool('pg_ctl'),'-D',str(data),'-m','fast','-w','stop'],env=env,stdout=log,stderr=log,timeout=30)
        log.close()
        if a.keep:print('Retained test cluster: '+str(root),flush=True)
        else:
            import shutil;shutil.rmtree(root)

if __name__=='__main__':sys.exit(main())
