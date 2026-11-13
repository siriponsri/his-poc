"""Private-tunnel ownership, identity and no-side-effect profile regressions."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from scripts import dr_train_tunnel as tunnel
from scripts import dev

MODEL = 'synthetic-model'
DIGEST = 'a' * 64
ENV = {'HIS_AI_PROVIDER': 'dr_train_ollama', 'DR_TRAIN_TUNNEL_ENABLED': 'true',
       'DR_TRAIN_SSH_TARGET': 'dr-train', 'DR_TRAIN_MODEL': MODEL,
       'DR_TRAIN_MODEL_DIGEST': DIGEST, 'DR_TRAIN_OLLAMA_VERSION': '0.12.6'}


def test_mock_or_disabled_profile_does_not_probe_start_or_touch_marker(monkeypatch):
    probe = Mock(side_effect=AssertionError('No socket expected'))
    monkeypatch.setattr(tunnel, 'listener_present', probe)
    monkeypatch.setattr(tunnel.subprocess, 'Popen', Mock(side_effect=AssertionError('No process expected')))
    assert tunnel.ensure_tunnel({})['status'] == 'NOT_REQUIRED'
    assert tunnel.ensure_tunnel({**ENV, 'HIS_AI_PROVIDER': 'mock_demo'})['status'] == 'NOT_REQUIRED'
    assert tunnel.ensure_tunnel({**ENV, 'DR_TRAIN_TUNNEL_ENABLED': 'false'})['status'] == 'NOT_REQUIRED'
    probe.assert_not_called()


def test_existing_verified_listener_reused_without_adopting_or_killing_pid(monkeypatch, tmp_path):
    config = replace(tunnel.TunnelConfig.from_env(ENV), state_dir=tmp_path)
    marker = tmp_path/'tunnel.json';marker.write_text('{"pid":7112,"unknown_owner":true}')
    monkeypatch.setattr(tunnel.TunnelConfig, 'from_env', lambda env: config)
    monkeypatch.setattr(tunnel, 'listener_present', lambda port: True)
    monkeypatch.setattr(tunnel, 'verify_listener', lambda cfg: {'status': 'PASS'})
    monkeypatch.setattr(tunnel.subprocess, 'Popen', Mock(side_effect=AssertionError('No process expected')))
    before = marker.read_bytes();result = tunnel.ensure_tunnel(ENV)
    assert result['listener'] == 'verified_existing' and result['process_ownership'] == 'not_assumed'
    assert marker.read_bytes() == before


def test_occupied_port_with_wrong_identity_fails_without_new_ssh_or_pid_kill(monkeypatch):
    monkeypatch.setattr(tunnel, 'listener_present', lambda port: True)
    def reject(_): raise tunnel.TunnelError('DR_TRAIN_TUNNEL_MODEL_MISMATCH')
    monkeypatch.setattr(tunnel, 'verify_listener', reject)
    monkeypatch.setattr(tunnel.subprocess, 'Popen', Mock(side_effect=AssertionError('No process expected')))
    with pytest.raises(tunnel.TunnelError, match='MODEL_MISMATCH'): tunnel.ensure_tunnel(ENV)


def test_native_metadata_identity_checks_exact_engine_and_digest():
    config = tunnel.TunnelConfig.from_env(ENV)
    def transport(digest=DIGEST, version='0.12.6'):
        def handle(request):
            assert request.url.host == '127.0.0.1'
            if request.url.path == '/api/version': return httpx.Response(200, json={'version': version})
            assert request.url.path == '/api/tags'
            return httpx.Response(200, json={'models': [{'name': MODEL, 'digest': digest}]})
        return httpx.MockTransport(handle)
    assert tunnel.verify_listener(config, transport=transport())['status'] == 'PASS'
    with pytest.raises(tunnel.TunnelError, match='MODEL_MISMATCH'): tunnel.verify_listener(config, transport=transport(digest='b'*64))
    with pytest.raises(tunnel.TunnelError, match='ENGINE_MISMATCH'): tunnel.verify_listener(config, transport=transport(version='0.0.0'))


def test_ssh_arguments_are_loopback_only_noninteractive_and_strict_known_host():
    config = tunnel.TunnelConfig.from_env(ENV)
    args = tunnel.ssh_arguments(config, 'ssh')
    assert args[-1] == 'dr-train' and '127.0.0.1:18134:127.0.0.1:11434' in args
    assert 'StrictHostKeyChecking=yes' in args and 'BatchMode=yes' in args
    assert 'ExitOnForwardFailure=yes' in args and '-N' in args and '-n' in args
    with pytest.raises(tunnel.TunnelError): tunnel.TunnelConfig.from_env({**ENV, 'DR_TRAIN_SSH_TARGET': '-oProxyCommand=bad'})


def test_status_not_running_does_not_start_ssh(monkeypatch):
    monkeypatch.setattr(tunnel, 'listener_present', lambda port: False)
    monkeypatch.setattr(tunnel.subprocess, 'Popen', Mock(side_effect=AssertionError('No process expected')))
    with pytest.raises(tunnel.TunnelError, match='NOT_RUNNING'): tunnel.ensure_tunnel(ENV, start=False)


@pytest.mark.parametrize('action', ['config', 'seed', 'status', 'logs', 'stop', 'native-seed'])
def test_launcher_read_config_seed_or_stop_never_starts_tunnel(monkeypatch, action):
    monkeypatch.setattr(dev.sys, 'argv', ['dev.py', action])
    monkeypatch.setattr(dev, 'load_env', lambda: dict(ENV))
    monkeypatch.setattr(dev, 'docker_preflight', lambda env: None)
    monkeypatch.setattr(dev, 'run', Mock())
    ensure = Mock(side_effect=AssertionError('No tunnel side effect expected'))
    monkeypatch.setattr(tunnel, 'ensure_tunnel', ensure)
    dev.main()
    ensure.assert_not_called()


def test_launcher_live_start_verifies_tunnel_before_application(monkeypatch):
    monkeypatch.setattr(dev.sys, 'argv', ['dev.py', 'start'])
    monkeypatch.setattr(dev, 'load_env', lambda: dict(ENV))
    order = []
    monkeypatch.setattr(dev, 'docker_preflight', lambda env: order.append('docker-preflight'))
    monkeypatch.setattr(dev, 'run', lambda *args, **kwargs: order.append('docker-command'))
    monkeypatch.setattr(dev, 'wait_web', lambda env: order.append('ready'))
    def verify(env):
        order.append('tunnel-verified');return {'status': 'PASS'}
    monkeypatch.setattr(tunnel, 'ensure_tunnel', verify)
    dev.main()
    assert order[:3] == ['docker-preflight', 'tunnel-verified', 'docker-command']
    assert order[-1] == 'ready'


def test_new_process_is_hidden_and_only_own_handle_cleanup_permitted(monkeypatch, tmp_path):
    config = replace(tunnel.TunnelConfig.from_env(ENV), state_dir=tmp_path)
    monkeypatch.setattr(tunnel.TunnelConfig, 'from_env', lambda env: config)
    probes = iter([False, True])
    monkeypatch.setattr(tunnel, 'listener_present', lambda port: next(probes))
    monkeypatch.setattr(tunnel.shutil, 'which', lambda name: 'ssh')
    process = Mock(pid=777);process.poll.return_value=None
    spawn = Mock(return_value=process);monkeypatch.setattr(tunnel.subprocess, 'Popen', spawn)
    monkeypatch.setattr(tunnel, 'verify_listener', lambda cfg: {'status': 'PASS'})
    result = tunnel.ensure_tunnel(ENV)
    assert result['listener'] == 'started' and (tmp_path/'tunnel.json').exists()
    assert spawn.call_args.kwargs['creationflags'] == getattr(tunnel.subprocess, 'CREATE_NO_WINDOW', 0)
    process.terminate.assert_not_called();process.kill.assert_not_called()
    # A subsequent failed verification may terminate only its just-created handle.
    probes = iter([False, True]);monkeypatch.setattr(tunnel, 'listener_present', lambda port: next(probes))
    def reject(_): raise tunnel.TunnelError('DR_TRAIN_TUNNEL_MODEL_MISMATCH')
    monkeypatch.setattr(tunnel, 'verify_listener', reject)
    with pytest.raises(tunnel.TunnelError): tunnel.ensure_tunnel(ENV)
    process.terminate.assert_called_once()
