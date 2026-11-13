"""Release integrity and private-file exclusion on reviewed source inventories."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_packaging', ROOT / 'scripts/package_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleasePackagingTests(unittest.TestCase):
    def test_even_explicitly_selected_secrets_runtime_and_archive_outputs_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            names = ['app.py', '.env.example', '.env', '.env.local', '.git/config',
                     'var/patient.json', 'private/patient.json', 'node_modules/lib.js',
                     'backup.dump', 'data/real.db', 'credentials.json', 'previous.zip',
                     'unusual-cluster/PG_VERSION', 'unusual-cluster/base/data', 'SHA256SUMS.json']
            for name in names:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'synthetic\r\n')
            output = root / 'release.zip'
            result = release.create_release(root, output, names + ['release.zip'])
            self.assertEqual(result['status'], 'PASS')
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {'app.py', '.env.example', 'SHA256SUMS.json'})
                self.assertEqual(archive.read('app.py'), b'synthetic\r\n')
                self.assertEqual(archive.read('SHA256SUMS.json'), (root / 'SHA256SUMS.json').read_bytes())
            self.assertEqual(set(json.loads((root / 'SHA256SUMS.json').read_text())), {'app.py', '.env.example'})

    def test_valid_zip_crc_cannot_hide_tampered_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'app.py').write_bytes(b'original')
            output = root / 'release.zip'
            release.create_release(root, output, ['app.py'])
            manifest = (root / 'SHA256SUMS.json').read_bytes()
            with zipfile.ZipFile(output, 'w') as archive:
                archive.writestr('app.py', b'tampered')
                archive.writestr('SHA256SUMS.json', manifest)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                release.verify_archive(output)

    def test_traversal_in_explicit_source_inventory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'relative'):
                release.selected_sources(Path(directory), ['../private.txt'])

    def test_source_change_before_publication_preserves_previous_archive_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'app.py'
            source.write_bytes(b'original')
            output = root / 'release.zip'
            output.write_bytes(b'previous archive')
            (root / 'SHA256SUMS.json').write_bytes(b'previous manifest')
            original_verify = release.verify_archive

            def mutate_after_verification(path):
                result = original_verify(path)
                source.write_bytes(b'concurrent change')
                return result

            with patch.object(release, 'verify_archive', side_effect=mutate_after_verification):
                with self.assertRaisesRegex(ValueError, 'changed before archive publication'):
                    release.create_release(root, output, ['app.py'])
            self.assertEqual(output.read_bytes(), b'previous archive')
            self.assertEqual((root / 'SHA256SUMS.json').read_bytes(), b'previous manifest')


if __name__ == '__main__':
    unittest.main()
