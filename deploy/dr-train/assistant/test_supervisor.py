"""Finite offline guard tests. Never invokes Docker, HTTP, DB or a model."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('supervisor', HERE / 'supervisor.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
APP_IMAGE = 'sha256:6e8ac411c0efae5e098b860006ff8de7428199973ebb8caa4500ac3b02936fa5'

class EndTest(BaseException):
    pass

class FakeFlock:
    LOCK_EX = 1; LOCK_NB = 2; LOCK_UN = 4
    @staticmethod
    def flock(*args):
        pass

class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((HERE / 'config.disabled.json').read_text())
        self.config.update(enabled=True, profiles_qualified=['visit_preparation'], worker_image_id=APP_IMAGE,
                           app_container='his-poc-server-app-1',app_compose_project='his-poc-server',app_compose_service='app',app_image_id=APP_IMAGE,
                           worker_env_sha256='2' * 64, engine_image_id='sha256:' + '3' * 64, engine_container_id='4' * 64,
                           engine_projection_sha256='5' * 64, gpu_uuid='GPU-00000000-0000-0000-0000-000000000000',
                           engine_base='http://192.168.1.2:11434', shared_base='http://127.0.0.1:11434', state_dir='/test-private')
        self.idle = {'engine_id':self.config['engine_container_id'], 'engine_image':self.config['engine_image_id'],
                     'app_name':self.config['app_container'],'app_image':APP_IMAGE,'app_project':'his-poc-server','app_service':'app','app_running':True,'app_health':'healthy',
                     'engine_gpu_ids':[self.config['gpu_uuid']], 'cuda_visible':self.config['gpu_uuid'], 'nvidia_visible':self.config['gpu_uuid'],
                     'engine_projection_sha256':self.config['engine_projection_sha256'], 'engine_running':True,
                     'version':'0.12.6', 'model_id':guard.MODEL, 'model_digest':guard.MODEL_DIGEST,
                     'gpu_free_mib':10000, 'gpu_compute_processes':[], 'shared_models':[], 'dedicated_models':[]}

    def test_disabled_unbound_template_cannot_dispatch(self):
        config = json.loads((HERE / 'config.disabled.json').read_text()); guard.validate(config)
        with self.assertRaises(ValueError): guard.validate(config, bound=True)

    def test_each_busy_or_identity_signal_denies(self):
        self.assertIsNone(guard.admission(self.idle,self.config))
        for field,value in [('gpu_free_mib',9999),('gpu_compute_processes',[99]),('shared_models',[{}]),('dedicated_models',[{}]),
                            ('engine_id','different'),('engine_projection_sha256','different'),('model_digest','different'),('engine_running',False),('engine_gpu_ids',['other'])]:
            with self.subTest(field=field):self.assertIsNotNone(guard.admission({**self.idle,field:value},self.config))

    def test_changed_fallback_wrong_project_or_unhealthy_app_denies_dispatch(self):
        for field,value in [('app_image','sha256:'+'0'*64),('app_name','other-app'),('app_project','other-project'),('app_service','other-service'),('app_running',False),('app_health','starting')]:
            with self.subTest(field=field):self.assertIsNotNone(guard.admission({**self.idle,field:value},self.config))

    def test_nonfinite_negative_or_unknown_gpu_memory_is_not_capacity(self):
        for value in [float('nan'),float('inf'),float('-inf'),-1,None,'10000',True]:
            with self.subTest(value=value):self.assertEqual(guard.admission({**self.idle,'gpu_free_mib':value},self.config),'GPU_MEMORY_METADATA_INVALID')

    def test_any_frozen_immutable_image_may_be_bound_but_worker_must_match(self):
        config=copy.deepcopy(self.config);config['app_image_id']='sha256:'+'a'*64;config['worker_image_id']=config['app_image_id']
        with patch.object(guard,'state_path',return_value=HERE):
            guard.validate(config,bound=True)
            config['worker_image_id']='sha256:'+'b'*64
            with self.assertRaises(ValueError):guard.validate(config,bound=True)

    def test_disabled_cli_verification_makes_zero_external_calls(self):
        with patch.object(sys,'argv',['supervisor.py','--config',str(HERE/'config.disabled.json'),'--verify-disabled']), \
             patch.object(guard,'observe') as observe,patch.object(guard,'run') as run,patch.object(guard.subprocess,'Popen') as popen,patch('builtins.print'):
            guard.main();observe.assert_not_called();run.assert_not_called();popen.assert_not_called()

    def test_fresh_second_busy_observation_prevents_popen(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            state=Path(directory); (state/'enabled').write_text('enabled')
            with patch.object(guard,'fcntl',FakeFlock),patch.object(guard,'private_dir'),patch.object(guard,'state_path',return_value=state), \
                 patch.object(guard,'observe',side_effect=[self.idle,{**self.idle,'gpu_compute_processes':[99]}]), \
                 patch.object(guard,'worker_command',return_value=['OFFLINE_NOT_RUN']),patch.object(guard,'run',return_value=''), \
                 patch.object(guard.subprocess,'Popen') as popen,patch.object(guard.time,'sleep',side_effect=EndTest):
                with self.assertRaises(EndTest):guard.supervise(copy.deepcopy(self.config))
                popen.assert_not_called()

    def test_halted_marker_prevents_any_new_observation_or_dispatch(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            state=Path(directory); (state/'HALTED_UNKNOWN.json').write_text('retained')
            with patch.object(guard,'fcntl',FakeFlock),patch.object(guard,'private_dir'),patch.object(guard,'state_path',return_value=state), \
                 patch.object(guard,'observe') as observe,patch.object(guard.subprocess,'Popen') as popen:
                guard.supervise(copy.deepcopy(self.config));observe.assert_not_called();popen.assert_not_called()
            self.assertEqual((state/'HALTED_UNKNOWN.json').read_text(),'retained')

    def test_tail_is_bounded_and_preserves_last_bytes(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            path=Path(directory)/'worker-output.tail'; raw=b'old'*100000+b'new'
            tail=guard.retain_tail(path,raw,262144)
            self.assertEqual(path.stat().st_size,262144);self.assertEqual(path.read_bytes(),raw[-262144:]);self.assertEqual(tail,raw[-262144:])

    def test_rotation_is_scoped_and_bounded(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            state=Path(directory);path=state/'ledger-private.jsonl';unrelated=state/'immutable-evidence.json';unrelated.write_text('preserve')
            for index in range(8):path.write_text(str(index));guard.rotate(path,4)
            self.assertEqual(len(list(state.glob('ledger-private.jsonl.*'))),4)
            self.assertEqual(unrelated.read_text(),'preserve')

if __name__=='__main__':unittest.main()
