"""Package reviewed source bytes only; exclude private runtime data even if tracked.

Default source inventory is Git tracked files, not a recursive copy of the worktree.
An explicit JSON array of relative source paths can be supplied without Git.
SHA256SUMS.json describes included working bytes; it excludes its own hash.
No Git changes, dependency installs, resets, deployments or external writes occur.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'SHA256SUMS.json'
EXCLUDED_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
                 '.mypy_cache', '.ruff_cache', '.test-out', 'dist', 'build', 'coverage',
                 'var', 'runtime', 'logs', 'backups', 'uploads', 'storage', 'private',
                 'secrets', 'pgdata', '.local', '.ssh', '.aws', '.azure', '.kube', '.terraform'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.db', '.sqlite', '.sqlite3', '.dump', '.dmp',
                     '.backup', '.bak', '.log', '.pem', '.key', '.p12', '.pfx',
                     '.zip', '.7z', '.tar', '.gz', '.tgz'}


def safe_name(name):
    name = str(name).replace('\\', '/')
    path = PurePosixPath(name)
    if not name or not path.parts or path.is_absolute() or '..' in path.parts or ':' in path.parts[0]:
        raise ValueError('Source paths must stay relative to the project: ' + name)
    return path.as_posix()


def excluded(name):
    path = PurePosixPath(safe_name(name))
    parts = [part.lower() for part in path.parts]
    base = parts[-1]
    return (any(part in EXCLUDED_DIRS for part in parts[:-1])
            or (base != '.env.example' and (base.startswith('.env') or base.endswith('.env') or '.env.' in base))
            or path.suffix.lower() in EXCLUDED_SUFFIXES
            or base in {'credentials.json', 'credential.json', 'secrets.json',
                        'cookies.json', 'session.json', 'pg_version', 'postmaster.pid'}
            or base.startswith(('private-key', 'id_rsa', 'id_ed25519'))
            or base.endswith(('.sql.gz', '.dump.sql', '.backup.sql')))


def source_names(root, source_list=None):
    if source_list:
        names = json.loads(Path(source_list).read_text(encoding='utf-8'))
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            raise ValueError('Source list must be a JSON array of relative paths')
    else:
        process = subprocess.run(['git', '-C', str(root), 'ls-files', '--cached', '-z'],
                                 capture_output=True)
        if process.returncode:
            raise RuntimeError('No Git source inventory; supply --source-list with reviewed relative paths')
        names = [os.fsdecode(name) for name in process.stdout.split(b'\0') if name]
    return sorted(set(safe_name(name) for name in names))


def selected_sources(root, names):
    root = Path(root).resolve()
    selected = {}
    for name in names:
        name = safe_name(name)
        if name == MANIFEST or excluded(name):
            continue
        path = root / name
        if path.is_symlink():
            raise ValueError('Symbolic links are not release source files: ' + name)
        try:
            resolved_name = path.resolve().relative_to(root).as_posix()
        except ValueError:
            raise ValueError('Source resolves outside the project: ' + name) from None
        if excluded(resolved_name):
            continue
        # A native PostgreSQL cluster is runtime data even under an unusual directory name.
        if any((parent / 'PG_VERSION').is_file() for parent in [path.parent, *path.parents]
               if parent != root and root in parent.parents):
            continue
        if not path.is_file():
            raise FileNotFoundError('Selected source is missing: ' + name)
        selected[name] = path
    if not selected:
        raise ValueError('No eligible reviewed source files selected')
    return selected


def verify_archive(archive):
    with zipfile.ZipFile(archive) as package:
        bad = package.testzip()
        if bad:
            raise ValueError('ZIP CRC failed: ' + bad)
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member names')
        hashes = json.loads(package.read(MANIFEST).decode('utf-8'))
        if not isinstance(hashes, dict) or MANIFEST in hashes:
            raise ValueError('Invalid source hash manifest')
        if set(names) != set(hashes) | {MANIFEST}:
            raise ValueError('ZIP members differ from the source hash manifest')
        for name, expected in hashes.items():
            if safe_name(name) != name or excluded(name):
                raise ValueError('Unsafe or private archive member: ' + name)
            if not isinstance(expected, str) or len(expected) != 64:
                raise ValueError('Invalid SHA256 for: ' + name)
            if hashlib.sha256(package.read(name)).hexdigest() != expected:
                raise ValueError('Source hash mismatch: ' + name)
    return {'status': 'PASS', 'crc': 'PASS', 'source_hashes': 'PASS', 'source_files': len(hashes),
            'zip_sha256': hashlib.sha256(Path(archive).read_bytes()).hexdigest()}


def create_release(root, output, names):
    root = Path(root).resolve()
    output = Path(output).resolve()
    if output.suffix.lower() != '.zip':
        raise ValueError('Release output must be a .zip file')
    sources = selected_sources(root, names)
    # Hash current working bytes, not the Git index or autocrlf-normalized blobs.
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()}
    manifest_bytes = (json.dumps(hashes, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=output.stem + '-', suffix='.zip', dir=output.parent)
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            for name, path in sources.items():
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != hashes[name]:
                    raise ValueError('Source changed while packaging; rerun after edits finish: ' + name)
                package.writestr(name, data)
            package.writestr(MANIFEST, manifest_bytes)
        result = verify_archive(temporary)
        for name, path in sources.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[name]:
                raise ValueError('Source changed before archive publication: ' + name)
        # Publish only a verified archive; no partial ZIP replaces a previous release.
        os.replace(temporary, output)
        (root / MANIFEST).write_bytes(manifest_bytes)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()
    return {**result, 'archive': str(output), 'manifest': str(root / MANIFEST),
            'source_bytes': 'current working files; no Git newline conversion'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--source-list', type=Path, help='Reviewed JSON array of relative source file paths')
    parser.add_argument('--verify-zip', type=Path, help='Only verify existing archive CRC, inventory and SHA256')
    args = parser.parse_args()
    if args.verify_zip:
        result = verify_archive(args.verify_zip)
    else:
        root = args.root.resolve()
        output = args.output or root.parent / (root.name + '-release.zip')
        result = create_release(root, output, source_names(root, args.source_list))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
