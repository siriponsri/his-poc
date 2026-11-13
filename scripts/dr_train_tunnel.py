"""Start/status of the explicit private SSH loopback route for HIS synthetic AI.

This changes only a local SSH process and private var/ marker/log files. It never
changes remote services, downloads models, runs inference, or kills a saved PID.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


class TunnelError(RuntimeError):
    """Fixed public codes only; no SSH command, key, endpoint or response body."""


@dataclass(frozen=True)
class TunnelConfig:
    target: str
    local_port: int
    remote_port: int
    ssh_port: int
    model: str
    model_digest: str
    engine_version: str
    state_dir: Path

    @classmethod
    def from_env(cls, env):
        try:
            config = cls(target=env.get('DR_TRAIN_SSH_TARGET', ''),
                         local_port=int(env.get('DR_TRAIN_TUNNEL_LOCAL_PORT', '18134')),
                         remote_port=int(env.get('DR_TRAIN_REMOTE_PORT', '11434')),
                         ssh_port=int(env.get('DR_TRAIN_SSH_PORT', '22')),
                         model=env.get('DR_TRAIN_MODEL', ''),
                         model_digest=env.get('DR_TRAIN_MODEL_DIGEST', ''),
                         engine_version=env.get('DR_TRAIN_OLLAMA_VERSION', ''),
                         state_dir=ROOT/'var'/'dr-train')
            if any(not 1 <= port <= 65535 for port in (config.local_port, config.remote_port, config.ssh_port)):
                raise ValueError('Invalid port')
            if config.target and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@:-]{0,200}', config.target):
                raise ValueError('Invalid SSH target')
            if not config.model or not re.fullmatch('[a-f0-9]{64}', config.model_digest) or not config.engine_version:
                raise ValueError('Missing expected identity')
            return config
        except (ValueError, TypeError, OverflowError):
            raise TunnelError('DR_TRAIN_TUNNEL_CONFIGURATION_INVALID') from None


def enabled(env):
    return (env.get('HIS_AI_PROVIDER') == 'dr_train_ollama' and
            env.get('DR_TRAIN_TUNNEL_ENABLED', '').lower() == 'true')


def listener_present(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            return True
    except OSError:
        return False


def verify_listener(config, *, transport=None):
    """Metadata reads only, through a fixed local origin; never triggers model load."""
    try:
        async def read_metadata():
            values = []
            async with asyncio.timeout(5):
                async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{config.local_port}', timeout=3,
                                             follow_redirects=False, trust_env=False, transport=transport) as client:
                    for path in ('/api/version', '/api/tags'):
                        async with client.stream('GET', path) as response:
                            if response.status_code != 200 or 'application/json' not in response.headers.get('content-type', '').lower():
                                raise TunnelError('DR_TRAIN_TUNNEL_IDENTITY_NOT_VERIFIED')
                            content = bytearray()
                            async for chunk in response.aiter_bytes():
                                content.extend(chunk)
                                if len(content) > 524288:
                                    raise TunnelError('DR_TRAIN_TUNNEL_IDENTITY_NOT_VERIFIED')
                            values.append(json.loads(content))
            return values
        version, tags = asyncio.run(read_metadata())
        if version.get('version') != config.engine_version:
            raise TunnelError('DR_TRAIN_TUNNEL_ENGINE_MISMATCH')
        models = tags.get('models')
        if not isinstance(models, list):
            raise TunnelError('DR_TRAIN_TUNNEL_MODEL_INVENTORY_INVALID')
        matches = [model for model in models if isinstance(model, dict) and model.get('name') == config.model]
        if len(matches) != 1 or matches[0].get('digest') != config.model_digest:
            raise TunnelError('DR_TRAIN_TUNNEL_MODEL_MISMATCH')
        return {'status': 'PASS', 'profile': 'private_ssh_loopback',
                'engine': 'ollama', 'engine_version': config.engine_version,
                'model': config.model, 'model_digest': config.model_digest,
                'metadata_only': True, 'local_port': config.local_port}
    except TunnelError:
        raise
    except (httpx.HTTPError, TimeoutError, ValueError, TypeError, AttributeError):
        raise TunnelError('DR_TRAIN_TUNNEL_NOT_READY') from None


def ssh_arguments(config, executable):
    if not config.target:
        raise TunnelError('DR_TRAIN_SSH_TARGET_REQUIRED')
    return [executable, '-N', '-n', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ConnectTimeout=8',
            '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
            '-p', str(config.ssh_port), '-L',
            f'127.0.0.1:{config.local_port}:127.0.0.1:{config.remote_port}', config.target]


def ensure_tunnel(env, *, start=True):
    if not enabled(env):
        return {'status': 'NOT_REQUIRED', 'reason': 'EXPLICIT_TUNNEL_PROFILE_NOT_ENABLED'}
    config = TunnelConfig.from_env(env)
    if listener_present(config.local_port):
        # A valid existing listener may belong to another task. Reuse its route,
        # but do not adopt/overwrite its marker and never terminate its PID.
        result = verify_listener(config)
        return {**result, 'listener': 'verified_existing', 'process_ownership': 'not_assumed'}
    if not start:
        raise TunnelError('DR_TRAIN_TUNNEL_NOT_RUNNING')
    executable = shutil.which('ssh')
    if not executable:
        raise TunnelError('SSH_EXECUTABLE_UNAVAILABLE')
    args = ssh_arguments(config, executable)
    config.state_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.state_dir/'ssh-tunnel.log'
    # This marker contains only process/route metadata; it is never a PID-kill authority.
    process = None
    with log_path.open('ab') as log:
        try:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       close_fds=True, cwd=ROOT, env=env,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise TunnelError('SSH_TUNNEL_START_FAILED')
                if listener_present(config.local_port):
                    result = verify_listener(config)
                    marker = {'managed_by': 'his-poc.dr-train-tunnel.v1', 'pid': process.pid,
                              'local_port': config.local_port, 'remote_port': config.remote_port,
                              'ssh_target_sha256': hashlib.sha256(config.target.encode()).hexdigest(),
                              'created_at_utc': datetime.now(timezone.utc).isoformat(),
                              'profile': 'private_ssh_loopback'}
                    temporary = config.state_dir/'tunnel.json.tmp'
                    temporary.write_text(json.dumps(marker, indent=2)+'\n', encoding='utf-8')
                    os.replace(temporary, config.state_dir/'tunnel.json')
                    return {**result, 'listener': 'started', 'process_ownership': 'started_by_this_call'}
                time.sleep(.25)
            raise TunnelError('SSH_TUNNEL_READINESS_TIMEOUT')
        except (OSError, TunnelError):
            # Only the process handle created in this call can be cleaned up.
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)
            raise TunnelError('SSH_TUNNEL_START_OR_VERIFICATION_FAILED') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status'])
    args = parser.parse_args()
    from dev import load_env
    try:
        result = ensure_tunnel(load_env(), start=args.action == 'start')
        print(json.dumps(result, indent=2))
        return 0
    except TunnelError as error:
        print(json.dumps({'status': 'FAIL', 'error_code': str(error)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
