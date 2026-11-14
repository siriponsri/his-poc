"""Scoped pause/status only. No resume, enable, retry, DB or model operation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
try:
    import fcntl
except ImportError:
    fcntl = None

def pause(state):
    if fcntl is None or not state.is_dir() or state.is_symlink():
        raise ValueError('EXISTING_PRIVATE_LINUX_STATE_REQUIRED')
    with (state / 'dispatch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = state / 'pause'
        if path.is_symlink():
            raise ValueError('SYMLINK_PAUSE')
        if not path.exists():
            with path.open('x') as output:
                output.write('PAUSED_BY_OPERATOR\n'); output.flush(); os.fsync(output.fileno())
            path.chmod(0o600)
        folder = os.open(state, os.O_DIRECTORY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    return {'state': 'PAUSED_NEW_DISPATCH', 'quiescence_proven': False, 'worker_cancelled': False, 'database_touched': False}

def status(state):
    if not state.is_dir() or state.is_symlink():
        raise ValueError('EXISTING_STATE_REQUIRED')
    result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=^/his-poc-assistant-worker-once$', '--format', '{{.ID}} {{.Status}}'], text=True, capture_output=True, timeout=5)
    if result.returncode:
        raise RuntimeError('WORKER_CONTAINER_STATE_UNKNOWN')
    return {'pause_present': (state / 'pause').exists(), 'enabled_sentinel_present': (state / 'enabled').exists(), 'halted_unknown_present': (state / 'HALTED_UNKNOWN.json').exists(),
            'named_worker_metadata': result.stdout.strip(), 'database_admission_checked': False, 'provider_drain_checked': False, 'quiescence_proven': False}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['pause', 'status']); parser.add_argument('--state', type=Path, required=True); args = parser.parse_args()
    print(json.dumps(pause(args.state) if args.action == 'pause' else status(args.state)))

if __name__ == '__main__':
    main()
