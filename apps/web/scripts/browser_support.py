"""CLI and credential-free provenance for local rendered acceptance checks."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import os
import platform
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]


def options(description, *, journeys=False, domains=None):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--base-url', default=os.getenv('HIS_BASE_URL', 'http://127.0.0.1:8000'),
                        help='Already running isolated synthetic app on loopback only')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'apps/web/evidence/fullsystem',
                        help='Evidence destination; use a new directory to preserve earlier runs')
    parser.add_argument('--headed', action='store_true', help='Show Chromium while checking the app')
    if journeys:
        parser.add_argument('--journeys', nargs='+', choices=[f'J{i:02}' for i in range(1,11)],
                            help='Run selected scenarios; omitted scenarios remain NOT_RUN')
    if domains:
        parser.add_argument('--domains', nargs='+', choices=domains,
                            help='Run selected domains; omitted domains remain NOT_RUN')
    args = parser.parse_args()
    os.environ['HIS_BASE_URL'] = args.base_url.rstrip('/')
    return args


def provenance():
    paths = []
    for directory in ['backend/app', 'apps/web/src', 'apps/web/scripts']:
        paths.extend(p for p in (ROOT/directory).rglob('*')
                     if p.is_file() and p.suffix in {'.py', '.json', '.tsx', '.ts', '.css'})
    return {'started_at_utc': datetime.now(timezone.utc).isoformat(),
            'command': [sys.executable, *sys.argv],
            'python_version': platform.python_version(), 'platform': platform.platform(),
            'base_url': os.getenv('HIS_BASE_URL', 'http://127.0.0.1:8000'),
            'data_profile': 'AUTHORED_SYNTHETIC',
            'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(paths)}}


def safe_error(error):
    frames=traceback.extract_tb(error.__traceback__)
    frame=frames[-1] if frames else None
    message=str(error) or (frame.line if frame else '') or 'Assertion failed'
    location=f' at {Path(frame.filename).name}:{frame.lineno}' if frame else ''
    return (type(error).__name__+location+': '+message).replace(os.getenv('HIS_SEED_PASSWORD', '') or '\0', '[REDACTED]')


def screenshot(page, output, name):
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output/(name+'.png')), full_page=True,
                    mask=[page.locator('input[type=password]')])


@contextmanager
def failure_artifacts(page, output, name):
    try:
        yield
    except Exception:
        try:
            screenshot(page() if callable(page) else page, output, name)
        except Exception:
            # Browser preflight failure must retain its original exception.
            pass
        raise
