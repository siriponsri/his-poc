"""Offline token/time/exclusive-consumption checks, never schedules cron."""
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('cron_launcher',HERE/'cron_launcher.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)

class CronRequestTests(unittest.TestCase):
    def files(self,state):
        token=state/'root-token-private';token.write_bytes(b'OFFLINE_NONSECRET_TEST_TOKEN')
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        value={'purpose':'VERIFY_ONLY','root_authorized':True,'request_id':'initial-verify','root_token_sha256':hashlib.sha256(token.read_bytes()).hexdigest(),
               'not_before_utc':now.isoformat(),'expires_utc':(now+timedelta(minutes=2)).isoformat()}
        request=state/'initial-request-private.json';request.write_text(json.dumps(value));return request,token,now

    def test_request_consumption_is_exclusive_and_does_not_replay(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            state=Path(directory);request,token,now=self.files(state)
            with patch.object(launcher,'read_private',side_effect=lambda path:path.read_bytes()):
                self.assertEqual(launcher.consume(request,token,state,now)['purpose'],'VERIFY_ONLY')
                with self.assertRaises(FileExistsError):launcher.consume(request,token,state,now)

    def test_expired_or_wrong_token_never_consumes(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            state=Path(directory);request,token,now=self.files(state)
            with patch.object(launcher,'read_private',side_effect=lambda path:path.read_bytes()):
                with self.assertRaises(ValueError):launcher.consume(request,token,state,now+timedelta(minutes=3))
                token.write_bytes(b'WRONG_OFFLINE_TOKEN')
                with self.assertRaises(ValueError):launcher.consume(request,token,state,now)
            self.assertFalse((state/'initial-verify-consumed.json').exists())

    def test_verify_mode_requires_disabled_unbound_configuration(self):
        config=json.loads((HERE/'config.disabled.json').read_text());launcher.validate_verify(config)
        config['enabled']=True
        with self.assertRaises(ValueError):launcher.validate_verify(config)

if __name__=='__main__':unittest.main()
