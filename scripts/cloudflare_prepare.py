"""Prepare a private, named Cloudflare Tunnel profile without publishing anything.

Writes only ignored var/cloudflare files. Does not authenticate, create a tunnel,
change DNS, start a service, seed, migrate, or send application data externally.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATE = ROOT / 'var' / 'cloudflare'
EXAMPLE = ROOT / 'deploy' / 'cloudflare' / 'settings.example.json'
KEYS = {'hostname', 'tunnel_id', 'credentials_file', 'access_team_name',
        'access_audience_tag', 'origin_port'}


class ProfileError(ValueError):
    """Fixed error codes; never echo credentials or arbitrary input."""


def validate_settings(value: object, *, require_credentials: bool = True) -> dict:
    if not isinstance(value, dict) or set(value) != KEYS:
        raise ProfileError('CLOUDFLARE_SETTINGS_KEYS_INVALID')
    hostname = value['hostname']
    if not isinstance(hostname, str) or hostname != hostname.lower() or len(hostname) > 253:
        raise ProfileError('CLOUDFLARE_HOSTNAME_INVALID')
    labels = hostname.split('.')
    if len(labels) < 2 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', x) for x in labels):
        raise ProfileError('CLOUDFLARE_HOSTNAME_INVALID')
    if hostname.endswith(('.example', '.invalid', '.test', '.localhost')) or hostname in {'example.com', 'example.org', 'example.net'} or hostname.endswith(('.example.com', '.example.org', '.example.net')):
        raise ProfileError('CLOUDFLARE_PLACEHOLDER_HOSTNAME')
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ProfileError('CLOUDFLARE_HOSTNAME_INVALID')
    try:
        tunnel_id = str(uuid.UUID(value['tunnel_id']))
        if uuid.UUID(tunnel_id).int == 0:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ProfileError('CLOUDFLARE_TUNNEL_ID_INVALID') from None
    team = value['access_team_name']
    if not isinstance(team, str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', team) or team in {'your-team', 'change-me'}:
        raise ProfileError('CLOUDFLARE_ACCESS_TEAM_INVALID')
    audience = value['access_audience_tag']
    if not isinstance(audience, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', audience) or len(set(audience.lower())) == 1:
        raise ProfileError('CLOUDFLARE_ACCESS_AUDIENCE_INVALID')
    port = value['origin_port']
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ProfileError('CLOUDFLARE_ORIGIN_PORT_INVALID')
    if not isinstance(value['credentials_file'], str) or not value['credentials_file']:
        raise ProfileError('CLOUDFLARE_CREDENTIALS_PATH_INVALID')
    credentials = Path(value['credentials_file']).expanduser()
    if not credentials.is_absolute():
        raise ProfileError('CLOUDFLARE_CREDENTIALS_PATH_MUST_BE_ABSOLUTE')
    credentials = credentials.resolve()
    if require_credentials:
        try:
            private = json.loads(credentials.read_text(encoding='utf-8-sig'))
            credential_id = str(uuid.UUID(private['TunnelID']))
            if credential_id != tunnel_id or not isinstance(private['TunnelSecret'], str) or len(private['TunnelSecret']) < 16 or not isinstance(private['AccountTag'], str) or not re.fullmatch('[a-fA-F0-9]{32}', private['AccountTag']):
                raise ValueError()
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            raise ProfileError('CLOUDFLARE_TUNNEL_CREDENTIALS_MISSING_OR_MISMATCHED') from None
    return dict(value, tunnel_id=tunnel_id, credentials_file=str(credentials))


def configuration(settings: dict) -> tuple[dict, dict]:
    """Return one hostname with mandatory Access validation and one-origin app."""
    tunnel = {'tunnel': settings['tunnel_id'],
              'credentials-file': settings['credentials_file'],
              'ingress': [{'hostname': settings['hostname'],
                           'service': f"http://127.0.0.1:{settings['origin_port']}",
                           'originRequest': {'access': {'required': True,
                                                       'teamName': settings['access_team_name'],
                                                       'audTag': [settings['access_audience_tag']]}}},
                          {'service': 'http_status:404'}]}
    override = {'services': {'app': {'environment': {
        'HIS_COOKIE_SECURE': 'true',
        'HIS_ENV': 'cloudflare_synthetic',
        'HIS_ALLOWED_ORIGINS': 'https://' + settings['hostname'],
        # Keep an application deadline below the documented edge read limit.
        'DR_TRAIN_TIMEOUT_SECONDS': '90',
    }}}}
    return tunnel, override


def load_settings(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        raise ProfileError('CLOUDFLARE_SETTINGS_MISSING_OR_INVALID') from None
    return validate_settings(raw)


def prepare(settings_path: Path, output_dir: Path = STATE) -> dict:
    settings = load_settings(settings_path)
    tunnel, override = configuration(settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in [('tunnel.json', tunnel), ('compose.override.json', override)]:
        path = output_dir / name
        path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return {'status': 'PREPARED_NOT_DEPLOYED', 'profile': 'named_tunnel_synthetic',
            'public_origin': 'https://' + settings['hostname'],
            'access_jwt_required': True, 'cookie_secure': True,
            'dr_train_timeout_seconds': 90,
            'note': 'No remote resource, DNS, service or application state changed.'}


def validate_prepared(settings_path: Path, output_dir: Path = STATE, *, use_cli: bool = True) -> dict:
    settings = load_settings(settings_path)
    tunnel, override = configuration(settings)
    try:
        for name, expected in [('tunnel.json', tunnel), ('compose.override.json', override)]:
            if json.loads((output_dir / name).read_text(encoding='utf-8')) != expected:
                raise ValueError()
    except (OSError, ValueError):
        raise ProfileError('CLOUDFLARE_PREPARED_FILES_STALE_OR_MISSING') from None
    if use_cli:
        executable = shutil.which('cloudflared')
        if not executable:
            raise ProfileError('CLOUDFLARED_EXECUTABLE_MISSING')
        # Syntax validation is offline and does not connect a tunnel.
        command = [executable, 'tunnel', '--config', str(output_dir / 'tunnel.json'), 'ingress', 'validate']
        try:
            result = subprocess.run(command, capture_output=True, timeout=15)
            if result.returncode:
                raise ProfileError('CLOUDFLARED_INGRESS_VALIDATION_FAILED')
        except (OSError, subprocess.TimeoutExpired):
            raise ProfileError('CLOUDFLARED_INGRESS_VALIDATION_FAILED') from None
        docker = shutil.which('docker')
        if not docker:
            raise ProfileError('DOCKER_COMPOSE_EXECUTABLE_MISSING')
        from scripts.dev import load_env
        command = [docker, 'compose', '-f', str(ROOT / 'compose.yaml'), '-f',
                   str(output_dir / 'compose.override.json'), 'config', '--format', 'json']
        try:
            process = subprocess.run(command, cwd=ROOT, env=load_env(),
                                     capture_output=True, text=True, timeout=20)
            if process.returncode:
                raise ValueError()
            resolved = json.loads(process.stdout)
            app = resolved['services']['app']
            env = app['environment']
            ports = app['ports']
            expected_env = override['services']['app']['environment']
            if any(str(env.get(key)) != expected for key, expected in expected_env.items()):
                raise ValueError()
            if len(ports) != 1 or ports[0]['host_ip'] != '127.0.0.1' or int(ports[0]['published']) != settings['origin_port'] or int(ports[0]['target']) != 8000 or resolved['services']['db'].get('ports'):
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
            raise ProfileError('CLOUDFLARE_COMPOSE_PROFILE_INVALID_OR_ORIGIN_PORT_MISMATCH') from None
    return {'status': 'LOCAL_PROFILE_VALIDATED_NOT_DEPLOYED',
            'public_origin': 'https://' + settings['hostname'],
            'access_policy_remote_verification': 'NOT_RUN',
            'dns_tunnel_external_browser': 'NOT_RUN',
            'note': 'Offline validation does not prove account ownership, DNS, policy or reachability.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'prepare', 'validate'])
    parser.add_argument('--settings', type=Path, default=STATE / 'settings.json')
    args = parser.parse_args(argv)
    try:
        if args.action == 'init':
            args.settings.parent.mkdir(parents=True, exist_ok=True)
            # Never overwrite private operator input.
            with args.settings.open('x', encoding='utf-8') as stream:
                stream.write(EXAMPLE.read_text(encoding='utf-8'))
            result = {'status': 'EXAMPLE_CREATED_NOT_CONFIGURED', 'next': 'Edit private settings, then prepare.'}
        elif args.action == 'prepare':
            result = prepare(args.settings)
        else:
            result = validate_prepared(args.settings)
        print(json.dumps(result, indent=2))
        return 0
    except FileExistsError:
        print(json.dumps({'status': 'RETAINED', 'code': 'PRIVATE_SETTINGS_ALREADY_EXIST'}))
        return 0
    except ProfileError as error:
        print(json.dumps({'status': 'NOT_READY', 'code': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
