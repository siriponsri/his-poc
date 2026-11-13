"""Deployment boundary regressions: private source packaging and loopback/Access contracts."""
from pathlib import Path
import importlib.util,json,tempfile,tarfile,unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('dr_train_deploy',ROOT/'scripts/dr_train_deploy.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class DeploymentBoundaries(unittest.TestCase):
 def test_snapshot_excludes_private_runtime_dependencies_and_preview(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   safe=['Dockerfile','.dockerignore','requirements-backend.txt','backend/app/main.py','apps/web/src/App.tsx','apps/web/public/logo.svg']
   private=['.env','var/server.env','apps/web/.env.production','apps/web/private_key.json','backend/credentials.json','backend/key.pem','apps/web/node_modules/dependency.js','apps/web/evidence/session.json','apps/web/vite.design.config.mts']
   for name in safe+private:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('private' if name in private else 'source')
   output=root/'candidate.tar.gz';result=module.snapshot(output,root)
   with tarfile.open(output) as tar:self.assertEqual(set(tar.getnames()),set(safe))
   self.assertEqual(set(result['source_sha256']),set(safe))
   with self.assertRaisesRegex(ValueError,'SNAPSHOT_ALREADY_EXISTS'):module.snapshot(output,root)
 def test_production_loopback_access_contract(self):
  self.assertEqual(module.validate_contract()['status'],'PASS')
 def test_public_origin_or_missing_access_cannot_validate(self):
  for target in ['public_bind','wrong_origin','access_bypass']:
   with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
    root=Path(directory);dest=root/'deploy/dr-train';dest.mkdir(parents=True)
    compose=json.loads((ROOT/'deploy/dr-train/compose.json').read_text());tunnel=json.loads((ROOT/'deploy/dr-train/tunnel.json').read_text())
    if target=='public_bind':compose['services']['app']['command'][-3]='0.0.0.0'
    elif target=='wrong_origin':compose['services']['app']['environment']['HIS_ALLOWED_ORIGINS']='*'
    else:tunnel['ingress'][0]['originRequest']['access']['required']=False
    (dest/'compose.json').write_text(json.dumps(compose));(dest/'tunnel.json').write_text(json.dumps(tunnel))
    with self.assertRaises(AssertionError):module.validate_contract(root)
if __name__=='__main__':unittest.main()
