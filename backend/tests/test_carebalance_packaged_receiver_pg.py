"""Exact allowlisted LabClear package on a separate disposable PostgreSQL DB."""
import os

assert os.environ.get("HIS_TEST_DATABASE_URL") == os.environ.get("DATABASE_URL") and os.environ.get("HIS_TEST_DATABASE_URL"), "Disposable PostgreSQL wrapper required"

import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tarfile
import time

import httpx
import pytest
from sqlalchemy import text

from backend.app import integrations as gateway
from backend.app.db import SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed
from backend.tests import test_carebalance_cross_app_pg as cross_app

ROOT = Path(__file__).resolve().parents[2]
LABCLEAR = ROOT.parent / "LabClear"
DATABASE = "carebalance_labclear_test_packaged_roundtrip"


@pytest.fixture(scope="module", autouse=True)
def explicit_seed():
    assert engine.url.database == "his_test"
    with SessionLocal.begin() as db:
        seed(db, os.environ["HIS_SEED_PASSWORD"])


@pytest.fixture(scope="module")
def packaged_receiver(tmp_path_factory):
    folder = tmp_path_factory.mktemp("carebalance-packaged-pg")
    state, package, guard = folder / "state", folder / "package", folder / "guard"
    for directory in (state, package, guard):
        directory.mkdir()
    python = LABCLEAR / ".venv/Scripts/python.exe"
    assert python.is_file()
    archive = folder / "source.tar"
    build = subprocess.run([str(python), str(LABCLEAR / "deploy/carebalance/build_source_bundle.py"),
                            "--output", str(archive)], capture_output=True, text=True, timeout=15)
    assert build.returncode == 0, build.stderr
    with tarfile.open(archive) as source:
        members = source.getmembers()
        assert all(member.isfile() and (package / member.name).resolve().is_relative_to(package.resolve())
                   for member in members)
        source.extractall(package, filter="data")
    manifest = json.loads((package / "SOURCE_MANIFEST.json").read_text())
    assert len(members) == 19
    for name, expected in manifest["source_sha256"].items():
        assert hashlib.sha256((package / name).read_bytes()).hexdigest() == expected
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as db:
        db.exec_driver_sql('CREATE DATABASE "' + DATABASE + '"')
    receiver_url = engine.url.set(drivername="postgresql", database=DATABASE).render_as_string(hide_password=False)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = {name: value for name, value in os.environ.items() if name.lower() in
                   {"systemroot", "windir", "path", "pathext", "temp", "tmp", "userprofile", "localappdata", "appdata", "comspec", "home"}}
    key = "synthetic-packaged-postgres-test-key-never-runtime"
    environment.update(PYTHONPATH=str(guard) + os.pathsep + str(package), APP_ENV="test",
        CAREBALANCE_INSTANCE_ID="carebalance-labclear-his-poc", CAREBALANCE_CONNECTOR_ENABLED="true",
        CAREBALANCE_CONNECTOR_KEY=key, BUSINESS_DATA_KEY=base64.urlsafe_b64encode(os.urandom(32)).decode(),
        PROVIDER_NETWORK_ENABLED="false", BUSINESS_EXTERNAL_ENABLED="false",
        DATABASE_URL=receiver_url, CAREBALANCE_EXPECTED_DATABASE=DATABASE)
    # Guard Python socket egress in the test child. libpq is separately bound by
    # the explicit URL and receiver's current_database identity check.
    (guard / "sitecustomize.py").write_text(
        "import socket,threading\n"
        "_connect,_pair,_lookup=socket.socket.connect,socket.socketpair,socket.getaddrinfo\n"
        "_internal=threading.local()\n"
        "def denied(*a,**k): raise RuntimeError('Test receiver outbound network denied')\n"
        "def pair(*a,**k):\n"
        " _internal.pair=True\n"
        " try: return _pair(*a,**k)\n"
        " finally: _internal.pair=False\n"
        "def connect(s,address):\n"
        " return _connect(s,address) if getattr(_internal,'pair',False) else denied()\n"
        "def lookup(host,*a,**k):\n"
        " return _lookup(host,*a,**k) if host in {'127.0.0.1','::1'} else denied()\n"
        "socket.socketpair=pair\nsocket.socket.connect=connect\nsocket.socket.connect_ex=denied\n"
        "socket.create_connection=denied\nsocket.getaddrinfo=lookup\n", encoding="utf-8")
    prepare_command = [str(python), str(package / "carebalance_receiver.py"), "prepare"]
    wrong = dict(environment, DATABASE_URL=engine.url.set(drivername="postgresql").render_as_string(hide_password=False))
    denied = subprocess.run(prepare_command, cwd=state, env=wrong, capture_output=True, text=True, timeout=15)
    assert denied.returncode != 0 and "database identity mismatch" in denied.stderr
    # Starting the server directly must fail closed too, before any route can
    # reach business_store's lazy schema creation or legacy guest migration.
    startup_command = [str(python), "-c", "import carebalance_receiver; carebalance_receiver.create_app()"]
    wrong_start = subprocess.run(startup_command, cwd=state, env=wrong, capture_output=True, text=True, timeout=15)
    assert wrong_start.returncode != 0 and "database identity mismatch" in wrong_start.stderr
    with engine.connect() as db:
        assert db.scalar(text("SELECT to_regclass('public.rs_entities')")) is None
        assert db.scalar(text("SELECT to_regclass('public.rs_mutex')")) is None
    unprepared = subprocess.run(startup_command, cwd=state, env=environment, capture_output=True, text=True, timeout=15)
    assert unprepared.returncode != 0 and "schema is not prepared" in unprepared.stderr
    import psycopg
    with psycopg.connect(receiver_url, autocommit=True) as unprepared_db:
        assert unprepared_db.execute("SELECT to_regclass('public.rs_entities'), to_regclass('public.rs_mutex')").fetchone() == (None, None)
    prepared = subprocess.run(prepare_command, cwd=state, env=environment, capture_output=True, text=True, timeout=15)
    assert prepared.returncode == 0, prepared.stderr
    command = [str(python), "-m", "uvicorn", "carebalance_receiver:create_app", "--factory", "--host",
               "127.0.0.1", "--port", str(port), "--workers", "1", "--no-access-log", "--log-level", "warning"]
    with (folder / "process.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=state, env=environment, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 20
            with httpx.Client(trust_env=False, timeout=0.5) as client:
                while time.monotonic() < deadline:
                    assert process.poll() is None, (folder / "process.log").read_text(encoding="utf-8")
                    try:
                        ready = client.get(f"http://127.0.0.1:{port}/ready")
                        if ready.status_code == 200:
                            assert ready.json()["ready"] is True
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("Exact packaged receiver did not become ready")
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setenv("HIS_LABCLEAR_ENABLED", "true")
            monkeypatch.setenv("HIS_LABCLEAR_ORIGIN", f"http://127.0.0.1:{port}")
            monkeypatch.setenv("HIS_LABCLEAR_KEY", key)
            assert gateway.resolve_client not in app.dependency_overrides
            try:
                yield {"origin": f"http://127.0.0.1:{port}", "url": receiver_url, "storage": "postgresql",
                       "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                       "source_sha256": manifest["source_sha256"]}
            finally:
                monkeypatch.undo()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            assert process.poll() is not None


def test_exact_package_separate_pg_his_import_human_review_and_readback(packaged_receiver):
    # Reuse the same real gateway journey assertions; this fixture substitutes
    # the exact deployment entrypoint and a separate PostgreSQL receiver DB.
    cross_app.test_real_http_import_human_correction_confirm_retry_and_readback(packaged_receiver)


def test_exact_package_scope_service_auth_and_database_isolation(packaged_receiver):
    cross_app.test_real_http_binding_scope_and_service_auth_remain_closed(packaged_receiver)
    import psycopg
    with psycopg.connect(packaged_receiver["url"], autocommit=True) as receiver:
        assert receiver.execute("SELECT current_database()").fetchone()[0] == DATABASE
        assert receiver.execute("SELECT count(*) FROM rs_entities WHERE kind='carebalance_report'").fetchone()[0] >= 1
        assert receiver.execute("SELECT count(*) FROM rs_entities WHERE kind='report'").fetchone()[0] == 0
        assert receiver.execute("SELECT to_regclass('public.connector_bindings')").fetchone()[0] is None
    with engine.connect() as his:
        assert his.scalar(text("SELECT current_database()")) == "his_test"
        assert his.scalar(text("SELECT to_regclass('public.rs_entities')")) is None
