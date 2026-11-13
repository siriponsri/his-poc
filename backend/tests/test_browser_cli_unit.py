"""Help must never turn a documentation request into browser mutations."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]


class BrowserCLI(unittest.TestCase):
 def test_help_without_credentials_does_not_create_evidence_or_launch_browser(self):
  env={k:v for k,v in os.environ.items() if k not in {'HIS_SEED_PASSWORD','HIS_BASE_URL'}}
  env.update(HIS_BASE_URL='https://not-a-local-app.invalid',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
  with tempfile.TemporaryDirectory() as temp:
   destination=Path(temp)/'must-not-exist'
   for name in ['browser_check.py','browser_journeys.py','browser_domains.py','browser_recovery.py','browser_live_ai.py']:
    with self.subTest(script=name):
     result=subprocess.run([sys.executable,str(ROOT/'apps/web/scripts'/name),'--output-dir',str(destination),'--help'],
       cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
     self.assertEqual(result.returncode,0,result.stderr)
     self.assertIn('usage:',result.stdout)
     self.assertFalse(destination.exists())


if __name__=='__main__':unittest.main()
