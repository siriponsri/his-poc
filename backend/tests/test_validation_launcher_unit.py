"""Validation portability and failure-reporting regressions; no PostgreSQL claims."""
import importlib.util,json,pathlib,subprocess,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('fullsystem_validation',ROOT/'scripts/validate_fullsystem.py')
validation=importlib.util.module_from_spec(spec);spec.loader.exec_module(validation)

class ValidationLauncherTests(unittest.TestCase):
 def test_windows_resolves_npm_and_build_precedes_http_smoke(self):
  with patch.object(validation.os,'name','nt'),patch.object(validation.shutil,'which',return_value=r'C:\Program Files\nodejs\npm.cmd') as which:
   cases=validation.validation_cases('pg18',True)
  which.assert_called_once_with('npm.cmd')
  self.assertEqual(cases[0][1][0],r'C:\Program Files\nodejs\npm.cmd')
  names=[name for name,_ in cases]
  self.assertLess(names.index('frontend-build'),names.index('same-origin'))
  for name in ['auth','clinical','erp']:
   self.assertIn(name+'-additional',names)
   self.assertIn('tests/fullsystem/test_'+name+'_acceptance.py',dict(cases)[name+'-additional'])
  self.assertIn('backend/tests/test_contract_export_unit.py',dict(cases)['launcher'])
  for filename in ['test_browser_restore_verifier_unit.py','test_browser_cli_unit.py']:
   self.assertIn('backend/tests/'+filename,dict(cases)['launcher'])
  self.assertIn('tests/fullsystem/test_security_event_concurrency.py',dict(cases)['security-event-concurrency'])

 def test_launch_failure_and_nonzero_exit_retained_without_stopping_later_checks(self):
  calls=[]
  def run(command,**kwargs):
   calls.append(command);self.assertEqual(kwargs['env']['PYTHONUTF8'],'1')
   if command[0]=='missing':raise FileNotFoundError('missing executable')
   return subprocess.CompletedProcess(command,7 if command[0]=='bad' else 0)
  snapshots=[{'sources':{'backend/app/main.py':'before'}},{'sources':{'backend/app/main.py':'after'}}]
  with tempfile.TemporaryDirectory() as directory,patch.object(validation.subprocess,'run',side_effect=run),patch.object(validation,'capture_provenance',side_effect=snapshots):
   output=pathlib.Path(directory)
   status=validation.run_cases([('missing',['missing']),('bad',['bad']),('ok',['ok'])],output)
   report=json.loads((output/'execution.json').read_text(encoding='utf-8'))
   self.assertEqual(status,1)
   self.assertEqual([r['exit_code'] for r in report],[127,7,0])
   self.assertEqual([r['status'] for r in report],['FAIL','FAIL','PASS'])
   self.assertIn('FileNotFoundError',(output/'missing.txt').read_text(encoding='utf-8'))
   self.assertEqual(len(calls),3)
   self.assertTrue(all(r['started_at'].endswith('+00:00') and r['completed_at'].endswith('+00:00') for r in report))
   manifest=json.loads((output/'run-manifest.json').read_text())
   self.assertEqual(manifest['status'],'FAIL')
   self.assertTrue(manifest['source_changed_during_run'])
   self.assertEqual(manifest['changed_sources_during_run'],['backend/app/main.py'])

 def test_source_inventory_excludes_secrets_and_dependencies_and_detects_changed_content(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(validation,'ROOT',pathlib.Path(directory)):
   root=pathlib.Path(directory)
   for relative in ['backend/app/main.py','backend/.env','backend/credentials.json','apps/web/src/index.ts','apps/web/src/node_modules/dep.js','config/policy.json']:
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic',encoding='utf-8')
   before=validation.source_inventory()
   self.assertEqual(set(before),{'backend/app/main.py','apps/web/src/index.ts','config/policy.json'})
   (root/'backend/app/main.py').write_text('changed',encoding='utf-8')
   after=validation.source_inventory()
   self.assertNotEqual(before['backend/app/main.py'],after['backend/app/main.py'])
   self.assertEqual(len(after['backend/app/main.py']),64)

if __name__=='__main__':unittest.main()
