"""Host resource fence for the real durable worker --once. Disabled by default.

This does not replace backend PostgreSQL admission, immutable stage evidence or
human approval. A GPU observation is not an exclusive reservation.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
import urllib.request
try:
    import fcntl
except ImportError:
    fcntl = None

PROFILES = {'visit_preparation', 'nursing_handover', 'records_readiness', 'laboratory_handoff'}
NAME = 'his-poc-assistant-worker-once'
UNIT = 'carebalance-assistant-worker.service'
MODEL = 'hf.co/scb10x/typhoon2.1-gemma3-12b-gguf:Q4_K_M'
MODEL_DIGEST = 'ab914ef406c9a78e2a8893eaa3b0ef78049f6c4e2703626433028e838d3a168b'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def now():
    return datetime.now(timezone.utc).isoformat()

def run(args, timeout=5):
    return subprocess.check_output(args, text=True, timeout=timeout)

def state_path(config):
    path = Path(config['state_dir']).expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('INVALID_STATE_PATH')
    return path

def validate(config, bound=False):
    if config['schema'] != 'carebalance.host-worker.v2' or config['worker_name'] != NAME:
        raise ValueError('INVALID_CONFIG')
    if config['model_id'] != MODEL or config['model_digest'] != MODEL_DIGEST or config['engine_version'] != '0.12.6':
        raise ValueError('INVALID_MODEL_PIN')
    if config['min_free_mib'] != 10000 or not 5 <= config['poll_seconds'] <= 60 or not 300 <= config['max_worker_seconds'] <= 480:
        raise ValueError('INVALID_BOUNDS')
    if config['ledger_bytes'] != 1048576 or config['ledger_copies'] != 4 or config['tail_bytes'] != 262144 or config['tail_copies'] != 12:
        raise ValueError('INVALID_RETENTION')
    if bound:
        if config['app_container'] != 'his-poc-server-app-1' or config['app_compose_project'] != 'his-poc-server' or config['app_compose_service'] != 'app':
            raise ValueError('UNBOUND_OR_DIFFERENT_ACTIVE_APP')
        if config['enabled'] is not True or not config['profiles_qualified'] or not set(config['profiles_qualified']) <= PROFILES:
            raise ValueError('WORKER_NOT_ENABLED_OR_QUALIFIED')
        for name in ['worker_image_id', 'engine_image_id', 'app_image_id']:
            if not re.fullmatch(r'sha256:[0-9a-f]{64}', config[name] or ''):
                raise ValueError('UNBOUND_IMAGE')
        if config['worker_image_id'] != config['app_image_id']:
            raise ValueError('WORKER_APP_IMAGE_MISMATCH')
        for name in ['worker_env_sha256', 'engine_container_id', 'engine_projection_sha256']:
            if not re.fullmatch(r'[0-9a-f]{64}', config[name] or ''):
                raise ValueError('UNBOUND_DIGEST')
        if not re.fullmatch(r'GPU-[0-9a-f-]{36}', config['gpu_uuid'] or ''):
            raise ValueError('UNBOUND_GPU')
        for name in ['engine_base', 'shared_base']:
            if not isinstance(config[name], str) or not re.fullmatch(r'http://(?:127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}):\d{2,5}', config[name]):
                raise ValueError('UNBOUND_PRIVATE_ENDPOINT')
        state_path(config)

def private_dir(path):
    if path.is_symlink():
        raise ValueError('SYMLINK_STATE')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_mode & 0o077:
        raise ValueError('STATE_MODE_NOT_PRIVATE')

def write_once(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, sort_keys=True); output.write('\n'); output.flush(); os.fsync(output.fileno())
    path.chmod(0o600)
    if os.name == 'posix':
        folder = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)

def rotate(path, copies):
    """Only our named disposable tails/ledger; immutable halt/history untouched."""
    if path.is_symlink():
        raise ValueError('SYMLINK_LOG')
    last = path.with_name(path.name + '.' + str(copies))
    if last.exists():
        if last.is_symlink():
            raise ValueError('SYMLINK_LOG')
        last.unlink()
    for index in range(copies - 1, 0, -1):
        old = path.with_name(path.name + '.' + str(index))
        if old.exists():
            if old.is_symlink():
                raise ValueError('SYMLINK_LOG')
            old.rename(path.with_name(path.name + '.' + str(index + 1)))
    if path.exists():
        if path.is_symlink():
            raise ValueError('SYMLINK_LOG')
        path.rename(path.with_name(path.name + '.1'))

def ledger(state, config, event):
    raw = canonical({'at': now(), 'supervisor_pid': os.getpid(), **event}) + b'\n'
    if len(raw) > 8192:
        raise ValueError('LEDGER_EVENT_TOO_LARGE')
    path = state / 'ledger-private.jsonl'
    if path.is_symlink():
        raise ValueError('SYMLINK_LOG')
    if path.exists() and path.stat().st_size + len(raw) > config['ledger_bytes']:
        rotate(path, config['ledger_copies'])
    with path.open('ab') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    path.chmod(0o600)

def projection(engine):
    env = dict(item.split('=', 1) for item in engine['Config']['Env'] if '=' in item)
    return {'id': engine['Id'], 'image': engine['Image'],
            'environment': {key: value for key, value in env.items() if key.startswith(('OLLAMA_', 'NVIDIA_', 'CUDA_'))},
            'cpu': engine['HostConfig']['NanoCpus'], 'memory': engine['HostConfig']['Memory'],
            'readonly': engine['HostConfig']['ReadonlyRootfs'], 'devices': engine['HostConfig']['DeviceRequests'],
            'mounts': sorted([{'source': mount['Source'], 'destination': mount['Destination'], 'rw': mount['RW']} for mount in engine['Mounts']], key=lambda item: item['destination']),
            'networks': {key: value['IPAddress'] for key, value in engine['NetworkSettings']['Networks'].items()}}

def observe(config):
    app = json.loads(run(['docker', 'inspect', config['app_container']]))[0]
    labels = app['Config'].get('Labels') or {}
    engine = json.loads(run(['docker', 'inspect', config['engine_container']]))[0]
    engine_env = dict(item.split('=', 1) for item in engine['Config']['Env'] if '=' in item)
    def get(base, path):
        request = urllib.request.Request(base + path, method='GET')
        # Disable proxy use and redirects; metadata only, never /chat or /generate.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, response, code, message, headers, url):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=3) as response:
            raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError('METADATA_TOO_LARGE')
            return json.loads(raw)
    gpu_rows = list(csv.reader(io.StringIO(run(['nvidia-smi', '--query-gpu=uuid,memory.free', '--format=csv,noheader,nounits']))))
    selected = [row for row in gpu_rows if row[0].strip() == config['gpu_uuid']]
    if len(selected) != 1:
        raise ValueError('GPU_NOT_IDENTIFIED')
    compute = [int(row[1].strip()) for row in csv.reader(io.StringIO(run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits']))) if len(row) == 2 and row[0].strip() == config['gpu_uuid']]
    tags = get(config['engine_base'], '/api/tags')['models']
    return {'app_name': app['Name'].lstrip('/'), 'app_image': app['Image'], 'app_project': labels.get('com.docker.compose.project'),
            'app_service': labels.get('com.docker.compose.service'), 'app_running': app['State']['Running'], 'app_health': app['State'].get('Health', {}).get('Status'),
            'engine_id': engine['Id'], 'engine_image': engine['Image'], 'engine_running': engine['State']['Running'],
            'engine_gpu_ids': engine['HostConfig']['DeviceRequests'][0]['DeviceIDs'],
            'cuda_visible': engine_env.get('CUDA_VISIBLE_DEVICES'), 'nvidia_visible': engine_env.get('NVIDIA_VISIBLE_DEVICES'),
            'engine_projection_sha256': sha(canonical(projection(engine))),
            'version': get(config['engine_base'], '/api/version')['version'],
            'model_id': tags[0]['name'] if len(tags) == 1 else None, 'model_digest': tags[0]['digest'] if len(tags) == 1 else None,
            'gpu_free_mib': float(selected[0][1]), 'gpu_compute_processes': compute,
            'shared_models': get(config['shared_base'], '/api/ps')['models'], 'dedicated_models': get(config['engine_base'], '/api/ps')['models']}

def admission(snapshot, config):
    if snapshot['app_name'] != config['app_container'] or snapshot['app_project'] != config['app_compose_project'] or snapshot['app_service'] != config['app_compose_service'] or snapshot['app_image'] != config['app_image_id']:
        return 'ACTIVE_APP_IDENTITY_CHANGED'
    if snapshot['app_running'] is not True or snapshot['app_health'] != 'healthy':
        return 'ACTIVE_APP_NOT_HEALTHY'
    for observed, expected in [('engine_id', 'engine_container_id'), ('engine_image', 'engine_image_id'), ('engine_projection_sha256', 'engine_projection_sha256'), ('version', 'engine_version'), ('model_id', 'model_id'), ('model_digest', 'model_digest')]:
        if snapshot[observed] != config[expected]:
            return 'IDENTITY_OR_RUNTIME_CHANGED'
    if not snapshot['engine_running']:
        return 'ENGINE_NOT_RUNNING'
    if snapshot['engine_gpu_ids'] != [config['gpu_uuid']] or snapshot['cuda_visible'] != config['gpu_uuid'] or snapshot['nvidia_visible'] != config['gpu_uuid']:
        return 'GPU_VISIBILITY_CHANGED'
    free = snapshot['gpu_free_mib']
    if isinstance(free, bool) or not isinstance(free, (int, float)) or not math.isfinite(free) or free < 0:
        return 'GPU_MEMORY_METADATA_INVALID'
    if free < config['min_free_mib'] or snapshot['gpu_compute_processes']:
        return 'GPU_BUSY'
    if snapshot['shared_models'] or snapshot['dedicated_models']:
        return 'MODEL_RESIDENT_BUSY'
    return None

def worker_command(config, state):
    original = Path(config['worker_env_file']).expanduser()
    if original.is_symlink():
        raise ValueError('SYMLINK_ENV')
    path = original.resolve()
    if not path.is_relative_to(state.resolve()) or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('ENV_NOT_PRIVATE_OR_SCOPED')
    if sha(path.read_bytes()) != config['worker_env_sha256']:
        raise ValueError('ENV_CHANGED')
    if json.loads(run(['docker', 'image', 'inspect', config['worker_image_id']]))[0]['Id'] != config['worker_image_id']:
        raise ValueError('WORKER_IMAGE_CHANGED')
    return ['docker', 'run', '--pull=never', '--rm', '--name', NAME, '--network', 'host', '--read-only', '--user', '10001:10001',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--tmpfs', '/tmp:rw,nosuid,noexec,size=128m', '--cpus', '1', '--memory', '1g', '--pids-limit', '128',
            '--env-file', str(path), '--env', 'PYTHONDONTWRITEBYTECODE=1', config['worker_image_id'], 'python', '-m', 'backend.app.assistant_worker', '--once']

def retain_tail(path, raw, maximum):
    if path.is_symlink():
        raise ValueError('SYMLINK_LOG')
    raw = raw[-maximum:]
    with path.open('wb') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    path.chmod(0o600)
    return raw

def monitor(worker, state, config, on_timeout):
    """Drain stdout without unbounded memory/disk. Never kill a timed-out worker."""
    path = state / 'worker-output.tail'
    rotate(path, config['tail_copies'])
    stream = worker.stdout; os.set_blocking(stream.fileno(), False)
    selector = selectors.DefaultSelector(); selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + config['max_worker_seconds']; tail = b''; timed_out = False
    try:
        while True:
            if not timed_out and time.monotonic() >= deadline:
                on_timeout(); timed_out = True
            for key, event in selector.select(timeout=.5):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if chunk:
                    tail = retain_tail(path, tail + chunk, config['tail_bytes'])
                else:
                    selector.unregister(stream)
            if worker.poll() is not None and not selector.get_map():
                return worker.returncode
    finally:
        selector.close()
        # A deadline fences new dispatch but keeps this bounded reader alive
        # until the CLI actually exits. It does not break an unknown worker's
        # stdout pipe or kill its CLI/model to manufacture quiescence.
        stream.close()

def halt(state, config, operation, worker, error_type):
    value = {'state': 'HALTED_UNKNOWN', 'at': now(), 'operation': operation, 'docker_cli_pid': worker.pid if worker else None,
             'container_name': NAME, 'error_type': error_type, 'automatic_retry': False, 'worker_or_model_killed': False}
    path = state / 'HALTED_UNKNOWN.json'
    if not path.exists():
        write_once(path, value)
    ledger(state, config, value)

def supervise(config):
    validate(config, bound=True)
    if fcntl is None:
        raise RuntimeError('LINUX_FLOCK_REQUIRED')
    state = state_path(config); private_dir(state)
    with (state / 'supervisor.lock').open('a') as singleton:
        fcntl.flock(singleton, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (state / 'dispatch.lock').open('a') as dispatch_lock:
            return supervisor_loop(config, state, dispatch_lock)

def supervisor_loop(config, state, dispatch_lock):
    if (state / 'HALTED_UNKNOWN.json').exists():
        return
    if (state / 'ACTIVE_DISPATCH.json').exists():
        halt(state, config, 'startup-reconciliation', None, 'PRIOR_DISPATCH_OUTCOME_UNKNOWN'); return
    while True:
        if (state / 'HALTED_UNKNOWN.json').exists():
            return
        if (state / 'ACTIVE_DISPATCH.json').exists():
            halt(state, config, 'loop-reconciliation', None, 'PRIOR_DISPATCH_OUTCOME_UNKNOWN'); return
        attempted = False; worker = None; operation = str(time.time_ns())
        try:
            if not (state / 'enabled').is_file() or (state / 'pause').exists():
                ledger(state, config, {'state': 'PAUSED_OR_DISABLED_NO_DISPATCH'}); time.sleep(config['poll_seconds']); continue
            reason = admission(observe(config), config)
            if reason:
                ledger(state, config, {'state': 'SKIPPED_RESOURCE', 'reason': reason, 'new_model_calls': 0}); time.sleep(config['poll_seconds']); continue
            command = worker_command(config, state)
            names = run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
            if NAME in names:
                halt(state, config, operation, None, 'EXISTING_WORKER_REQUIRES_RECONCILIATION'); return
            fcntl.flock(dispatch_lock, fcntl.LOCK_EX)
            try:
                if not (state / 'enabled').is_file() or (state / 'pause').exists():
                    continue
                reason = admission(observe(config), config)
                if reason:
                    ledger(state, config, {'state': 'SKIPPED_FRESH_RECHECK', 'reason': reason, 'new_model_calls': 0})
                else:
                    ledger(state, config, {'state': 'DISPATCHING_ONE_WORKER_ONCE', 'operation': operation, 'image_id': config['worker_image_id'], 'maximum_preparations': 1})
                    write_once(state / 'ACTIVE_DISPATCH.json', {'operation': operation, 'at': now(), 'image_id': config['worker_image_id'], 'outcome': 'UNKNOWN_UNTIL_KNOWN_WORKER_EXIT'})
                    attempted = True
                    worker = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    ledger(state, config, {'state': 'WORKER_ACTIVE', 'operation': operation, 'docker_cli_pid': worker.pid})
            finally:
                fcntl.flock(dispatch_lock, fcntl.LOCK_UN)
            if worker is not None:
                result = monitor(worker, state, config, lambda: halt(state, config, operation, worker, 'WORKER_DEADLINE_REMOTE_UNKNOWN'))
                if (state / 'HALTED_UNKNOWN.json').exists():
                    return
                if result != 0:
                    halt(state, config, operation, worker, 'WORKER_UNKNOWN_OR_NONZERO'); return
                ledger(state, config, {'state': 'WORKER_EXITED', 'operation': operation, 'exit_code': 0})
                (state / 'ACTIVE_DISPATCH.json').unlink()
            time.sleep(config['poll_seconds'])
        except Exception as error:
            if attempted:
                halt(state, config, operation, worker, type(error).__name__); return
            ledger(state, config, {'state': 'SKIPPED_PREFLIGHT_ERROR', 'error_type': type(error).__name__, 'new_model_calls': 0})
            time.sleep(config['poll_seconds'])

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True); modes.add_argument('--verify-disabled', action='store_true'); modes.add_argument('--run', action='store_true')
    args = parser.parse_args(); config = json.loads(args.config.read_text()); validate(config)
    if args.verify_disabled:
        if config['enabled'] is not False or config['worker_image_id'] is not None or config['worker_env_sha256'] is not None or config['profiles_qualified']:
            raise ValueError('EXPECTED_DISABLED_UNBOUND_CONFIG')
        print(json.dumps({'status': 'PASS_DISABLED_UNBOUND_NO_DISPATCH', 'docker_calls': 0, 'http_calls': 0, 'database_calls': 0})); return
    supervise(config)

if __name__ == '__main__':
    main()
