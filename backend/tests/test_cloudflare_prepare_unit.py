"""Offline deployment-profile guards; no Cloudflare account or public deployment."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cloudflare_prepare', ROOT / 'scripts/cloudflare_prepare.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class CloudflareProfileTests(unittest.TestCase):
    def settings(self, directory):
        credentials = Path(directory) / 'private-tunnel.json'
        value = {'hostname': 'his.hospital-owner.org',
                 'tunnel_id': 'f91849aa-0f36-48b9-9de7-2a994315ca86',
                 'credentials_file': str(credentials.resolve()),
                 'access_team_name': 'hospital-owner',
                 'access_audience_tag': 'a1b2c3d4' * 8,
                 'origin_port': 8000}
        credentials.write_text(json.dumps({'TunnelID': value['tunnel_id'],
                                         'TunnelSecret': 'SYNTHETIC_TEST_ONLY_NOT_A_REAL_SECRET',
                                         'AccountTag': 'a1b2c3d4' * 4}))
        return value

    def test_example_fails_closed_before_any_outbound_or_generated_profile(self):
        value = json.loads(profile.EXAMPLE.read_text())
        with self.assertRaisesRegex(profile.ProfileError, 'PLACEHOLDER_HOSTNAME'):
            profile.validate_settings(value)

    def test_requires_exact_settings_keys(self):
        with self.assertRaisesRegex(profile.ProfileError, 'KEYS_INVALID'):
            profile.validate_settings({'hostname': 'his.hospital-owner.org'})

    def test_hostname_cannot_inject_url_path_port_wildcard_or_ip(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            for hostname in ['http://his.hospital-owner.org', '*.hospital-owner.org',
                             'his.hospital-owner.org/path', 'his.hospital-owner.org:443',
                             '127.0.0.1', 'localhost', 'his..org', 'his.example.com']:
                with self.subTest(hostname=hostname), self.assertRaises(profile.ProfileError):
                    profile.validate_settings(dict(value, hostname=hostname))

    def test_requires_access_team_and_nonplaceholder_audience(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            for changes in [{'access_team_name': ''}, {'access_team_name': 'your-team'},
                            {'access_team_name': 'team.cloudflareaccess.com'},
                            {'access_audience_tag': ''}, {'access_audience_tag': '0' * 64},
                            {'access_audience_tag': 'a' * 63 + '\n'}]:
                with self.subTest(changes=changes), self.assertRaises(profile.ProfileError):
                    profile.validate_settings(dict(value, **changes))

    def test_credentials_must_match_tunnel_and_never_appear_in_generated_content(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            settings = profile.validate_settings(value)
            tunnel, override = profile.configuration(settings)
            text = json.dumps([tunnel, override])
            self.assertNotIn('SYNTHETIC_TEST_ONLY', text)
            self.assertNotIn('AccountTag', text)
            value['tunnel_id'] = 'd17351d0-e37b-44ab-879f-2a6bb7869a03'
            with self.assertRaisesRegex(profile.ProfileError, 'CREDENTIALS_MISSING_OR_MISMATCHED'):
                profile.validate_settings(value)

    def test_requires_absolute_existing_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            with self.assertRaisesRegex(profile.ProfileError, 'MUST_BE_ABSOLUTE'):
                profile.validate_settings(dict(value, credentials_file='relative.json'))
            Path(value['credentials_file']).unlink()
            with self.assertRaisesRegex(profile.ProfileError, 'CREDENTIALS_MISSING_OR_MISMATCHED'):
                profile.validate_settings(value)

    def test_invalid_tunnel_ids_and_ports(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            for changes in [{'tunnel_id': ''}, {'tunnel_id': '0' * 32},
                            {'origin_port': 0}, {'origin_port': 65536},
                            {'origin_port': '8000'}, {'origin_port': True}]:
                with self.subTest(changes=changes), self.assertRaises(profile.ProfileError):
                    profile.validate_settings(dict(value, **changes))

    def test_profile_has_one_loopback_origin_access_required_and_deny_catchall(self):
        with tempfile.TemporaryDirectory() as directory:
            tunnel, override = profile.configuration(profile.validate_settings(self.settings(directory)))
            ingress = tunnel['ingress']
            self.assertEqual(len(ingress), 2)
            self.assertEqual(ingress[0]['service'], 'http://127.0.0.1:8000')
            self.assertTrue(ingress[0]['originRequest']['access']['required'])
            self.assertEqual(ingress[1], {'service': 'http_status:404'})
            env = override['services']['app']['environment']
            self.assertEqual(env['HIS_ALLOWED_ORIGINS'], 'https://his.hospital-owner.org')
            self.assertEqual(env['HIS_COOKIE_SECURE'], 'true')
            self.assertEqual(env['DR_TRAIN_TIMEOUT_SECONDS'], '90')
            self.assertNotIn('ports', override['services']['app'])
            self.assertNotIn('db', override['services'])

    def test_prepare_validate_offline_and_detect_tampered_access(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            settings = Path(directory) / 'settings.json'
            settings.write_text(json.dumps(value))
            output = Path(directory) / 'generated'
            self.assertEqual(profile.prepare(settings, output)['status'], 'PREPARED_NOT_DEPLOYED')
            self.assertEqual(profile.validate_prepared(settings, output, use_cli=False)['status'],
                             'LOCAL_PROFILE_VALIDATED_NOT_DEPLOYED')
            tunnel = json.loads((output / 'tunnel.json').read_text())
            tunnel['ingress'][0]['originRequest']['access']['required'] = False
            (output / 'tunnel.json').write_text(json.dumps(tunnel))
            with self.assertRaisesRegex(profile.ProfileError, 'STALE_OR_MISSING'):
                profile.validate_prepared(settings, output, use_cli=False)

    def test_cloudflared_validation_failure_is_not_ready_and_output_is_not_echoed(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            settings = Path(directory) / 'settings.json'
            settings.write_text(json.dumps(value))
            output = Path(directory) / 'generated'
            profile.prepare(settings, output)
            with patch.object(profile.shutil, 'which', return_value='cloudflared'), \
                 patch.object(profile.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, stdout=b'private body')):
                with self.assertRaisesRegex(profile.ProfileError, '^CLOUDFLARED_INGRESS_VALIDATION_FAILED$'):
                    profile.validate_prepared(settings, output)

    def test_help_never_loads_settings_or_creates_files(self):
        with patch.object(profile, 'load_settings', side_effect=AssertionError('must not read settings')):
            with self.assertRaises(SystemExit) as exited:
                profile.main(['--help'])
            self.assertEqual(exited.exception.code, 0)

    def test_resolved_compose_port_must_match_tunnel_and_database_stays_private(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.settings(directory)
            settings = Path(directory) / 'settings.json'
            settings.write_text(json.dumps(value))
            output = Path(directory) / 'generated'
            profile.prepare(settings, output)
            expected = profile.configuration(value)[1]['services']['app']['environment']
            for ports, db_ports in [([{'host_ip': '0.0.0.0', 'published': '8000', 'target': 8000}], []),
                                    ([{'host_ip': '127.0.0.1', 'published': '9000', 'target': 8000}], []),
                                    ([{'host_ip': '127.0.0.1', 'published': '8000', 'target': 8000}], ['5432:5432'])]:
                resolved = {'services': {'app': {'environment': expected, 'ports': ports},
                                         'db': {'ports': db_ports}}}
                results = [subprocess.CompletedProcess([], 0),
                           subprocess.CompletedProcess([], 0, stdout=json.dumps(resolved))]
                with self.subTest(ports=ports, db_ports=db_ports), \
                     patch.object(profile.shutil, 'which', return_value='test-tool'), \
                     patch.object(profile.subprocess, 'run', side_effect=results), \
                     patch('scripts.dev.load_env', return_value={}):
                    with self.assertRaisesRegex(profile.ProfileError, 'COMPOSE_PROFILE_INVALID_OR_ORIGIN_PORT_MISMATCH'):
                        profile.validate_prepared(settings, output)


if __name__ == '__main__':
    unittest.main()
