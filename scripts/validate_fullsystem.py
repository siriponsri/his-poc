"""Reproduce independent PostgreSQL suites; no deployment, reset or live inference.
Requires installed locked Python/Node deps and PostgreSQL18 binaries.
"""
from pathlib import Path
import argparse,subprocess,sys,json,time,os,shutil,hashlib,platform
from datetime import datetime,timezone
from importlib.metadata import version,PackageNotFoundError
ROOT=Path(__file__).resolve().parents[1]

def utc_now():
 return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

def source_inventory():
 """Hashes only: explicit source roots, no environment or private runtime files."""
 allowed={'.py','.ts','.tsx','.js','.mjs','.json','.sql','.md','.toml','.yaml','.yml','.ini','.csv','.txt','.svg'}
 excluded={'node_modules','__pycache__','.git','.venv','dist','evidence','.pytest_cache','var'}
 files=[]
 for directory in ['backend','scripts','apps/web/src','apps/web/scripts','apps/web/tests','tests','contracts','spec','config']:
  for path in (ROOT/directory).rglob('*'):
   if not path.is_file() or path.is_symlink():continue
   relative=path.relative_to(ROOT)
   if any(part in excluded or part.startswith('.env') for part in relative.parts):continue
   if path.suffix.lower() not in allowed:continue
   if any(word in path.name.lower() for word in ['credential','secret','private-key']):continue
   files.append(path)
 for name in ['AGENTS.md','START_HERE.md','GOAL.md','PLAN.md','BACKLOG.md','CODEX_HANDOFF.md','VALIDATION_REPORT.md','DOMAIN_COVERAGE.json','JOURNEY_COVERAGE.json','requirements-backend.txt','requirements-validation.txt','apps/web/package.json','apps/web/package-lock.json']:
  if (ROOT/name).is_file():files.append(ROOT/name)
 return {path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(set(files))}

def runtime_versions(pg_bin=None):
 result={'platform':platform.platform(),'python':platform.python_version(),'python_executable':sys.executable,'libraries':{}}
 for package in ['fastapi','SQLAlchemy','alembic','psycopg','playwright','pytest']:
  try:result['libraries'][package]=version(package)
  except PackageNotFoundError:result['libraries'][package]=None
 executables={'node':shutil.which('node')}
 if pg_bin:executables['postgres']=str(Path(pg_bin)/('postgres.exe' if os.name=='nt' else 'postgres'))
 for name,executable in executables.items():
  result[name]=None
  if not executable:continue
  try:
   process=subprocess.run([executable,'--version'],capture_output=True,text=True,encoding='utf-8',timeout=10)
   if process.returncode==0:result[name]=process.stdout.strip()
  except (OSError,subprocess.TimeoutExpired):pass
 return result

def capture_provenance(pg_bin=None):
 return {'observed_at':utc_now(),'scope':'Source snapshot at observation time; not retroactive proof of earlier executions',
         'algorithm':'sha256','sources':source_inventory(),'runtime':runtime_versions(pg_bin)}

def write_source_manifest(output,pg_bin=None,filename='source-manifest.json'):
 """Standalone snapshot for an existing evidence directory; never backdates a run."""
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 path=output/filename
 path.write_text(json.dumps(capture_provenance(pg_bin),indent=2)+'\n',encoding='utf-8')
 return path
def validation_cases(pg_bin, include_frontend=False):
 wrapper=[sys.executable,'scripts/test_with_postgres.py','--pg-bin',pg_bin,'--',sys.executable]
 cases=[('seed',wrapper+['scripts/verify_seed.py']),('core',wrapper+['backend/tests/run_core_validation.py']),('clinical',wrapper+['scripts/run_pg_suite.py','tests/fullsystem/test_clinical.py','-q']),('erp',wrapper+['-m','pytest','tests/fullsystem/test_erp.py','-q']),('operations',wrapper+['-m','pytest','backend/tests/test_operations_pg.py','-q']),('launcher',[sys.executable,'-m','pytest','backend/tests/test_operations_unit.py','-q']),('same-origin',wrapper+['scripts/verify_same_origin.py']),('package',[sys.executable,'scripts/check_fullsystem_package.py'])]
 if include_frontend:
  # CreateProcess does not apply PATHEXT like a shell: resolve npm.cmd on Windows.
  npm_name='npm.cmd' if os.name=='nt' else 'npm'
  npm=shutil.which(npm_name) or npm_name
  # Build before same-origin smoke so a fresh checkout has served assets.
  cases=[('frontend-'+name,[npm,'--prefix','apps/web','run',name]) for name in ['test','test:component','test:audit','typecheck','build']]+cases
 for name,command in cases:
  if name=='launcher':command[-1:-1]=['backend/tests/test_validation_launcher_unit.py','backend/tests/test_catalog_encoding_unit.py','backend/tests/test_release_packaging_unit.py','backend/tests/test_contract_export_unit.py','backend/tests/test_browser_restore_verifier_unit.py','backend/tests/test_browser_cli_unit.py']
 for name in ['auth','clinical','erp']:
  cases.append((name+'-additional',wrapper+['-m','pytest','tests/fullsystem/test_'+name+'_acceptance.py','-q']))
 cases.append(('security-event-concurrency',wrapper+['-m','pytest','tests/fullsystem/test_security_event_concurrency.py','-q']))
 return cases

def run_cases(cases, output, pg_bin=None):
 output.mkdir(parents=True,exist_ok=True)
 started_at=utc_now();before=capture_provenance(pg_bin)
 (output/'source-start.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
 env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
 results=[]
 for name,cmd in cases:
  start=time.time();check_started_at=utc_now();log_path=output/(name.replace(':','-')+'.txt')
  with log_path.open('w',encoding='utf-8') as log:
   try:code=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
   except OSError as exc:
    # Missing executables must not discard the remaining checks or their exit codes.
    log.write(f'{type(exc).__name__}: {exc}\n');code=127
  try:evidence_path=str(log_path.relative_to(ROOT))
  except ValueError:evidence_path=str(log_path)
  item={'check':name,'command':cmd,'started_at':check_started_at,'completed_at':utc_now(),'exit_code':code,'status':'PASS' if code==0 else 'FAIL','duration_seconds':round(time.time()-start,3),'log':evidence_path}
  results.append(item);print(json.dumps(item),flush=True)
  (output/'execution.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
 after=capture_provenance(pg_bin)
 (output/'source-end.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
 changed=sorted(name for name in set(before['sources'])|set(after['sources']) if before['sources'].get(name)!=after['sources'].get(name))
 summary={'started_at':started_at,'completed_at':utc_now(),'source_start':'source-start.json','source_end':'source-end.json','changed_sources_during_run':changed,'source_changed_during_run':bool(changed),'checks':len(results),'status':'FAIL' if any(x['exit_code'] for x in results) else 'PASS','note':'Each command has UTC timestamps in execution.json; source changes are disclosed and require review before binding acceptance to one candidate.'}
 (output/'run-manifest.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
 return int(any(x['exit_code'] for x in results))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pg-bin',required=True);p.add_argument('--include-frontend',action='store_true')
 p.add_argument('--output-dir',type=Path,default=ROOT/'evidence/fullsystem/final',help='Use a new directory to preserve earlier run logs')
 a=p.parse_args()
 return run_cases(validation_cases(a.pg_bin,a.include_frontend),a.output_dir.resolve(),a.pg_bin)

if __name__=='__main__':sys.exit(main())
