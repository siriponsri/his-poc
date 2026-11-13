"""Launcher safety tests do not claim Docker/PostgreSQL execution."""
import importlib.util,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('his_dev_launcher',ROOT/'scripts/dev.py');dev=importlib.util.module_from_spec(spec);spec.loader.exec_module(dev)

class LauncherSafety(unittest.TestCase):
    def test_initialize_preserves_existing_private_configuration(self):
        with tempfile.TemporaryDirectory() as d,patch.object(dev,'ROOT',pathlib.Path(d)):
            dev.initialize();p=pathlib.Path(d)/'.env';before=p.read_bytes();dev.initialize();self.assertEqual(p.read_bytes(),before)
            self.assertNotIn(b'CHANGE_ME',before)
    def test_migration_failure_prevents_seed_and_app(self):
        calls=[]
        def fake_run(args,**kw):
            calls.append(args)
            if 'upgrade' in args:raise dev.subprocess.CalledProcessError(1,args)
        with patch.object(dev,'docker_preflight'),patch.object(dev,'load_env',return_value={}),patch.object(dev,'run',side_effect=fake_run),patch.object(dev.sys,'argv',['dev.py','up']):
            with self.assertRaises(dev.subprocess.CalledProcessError):dev.main()
        self.assertFalse(any('backend.app.seed' in c for c in calls));self.assertFalse(any(c[-1]=='app' and 'up' in c for c in calls))
    def test_first_start_order(self):
        calls=[]
        with patch.object(dev,'docker_preflight'),patch.object(dev,'load_env',return_value={}),patch.object(dev,'run',side_effect=lambda args,**kw:calls.append(args)),patch.object(dev,'wait_web'),patch.object(dev.sys,'argv',['dev.py','up']):dev.main()
        self.assertEqual(calls[0][-1],'db');self.assertIn('--wait',calls[0]);self.assertIn('upgrade',calls[2]);self.assertIn('backend.app.seed',calls[3]);self.assertEqual(calls[4][-1],'app')
    def test_restart_does_not_seed(self):
        calls=[]
        with patch.object(dev,'docker_preflight'),patch.object(dev,'load_env',return_value={}),patch.object(dev,'run',side_effect=lambda args,**kw:calls.append(args)),patch.object(dev,'wait_web'),patch.object(dev.sys,'argv',['dev.py','start']):dev.main()
        self.assertFalse(any('backend.app.seed' in c for c in calls))
    def test_native_refuses_sqlite(self):
        with self.assertRaisesRegex(RuntimeError,'PostgreSQL'):dev.native({'DATABASE_URL':'sqlite:///fake.db'})
    def test_no_docker_clear_failure(self):
        with patch.object(dev.shutil,'which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'Docker executable is unavailable'):dev.docker_preflight({})

if __name__=='__main__':unittest.main()
