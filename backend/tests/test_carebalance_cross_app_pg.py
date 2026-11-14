"""Real HIS PostgreSQL/session gateway -> loopback HTTP -> real LabClear receiver.

LabClear uses a fresh encrypted SQLite test store in a separate process. This
proves this integration transport/workflow, not LabClear PostgreSQL deployment.
"""
import os

assert os.environ.get("HIS_TEST_DATABASE_URL") == os.environ.get("DATABASE_URL") and os.environ.get("HIS_TEST_DATABASE_URL"), "Disposable PostgreSQL wrapper required"

from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

from backend.app import integrations as gateway
from backend.app.db import SessionLocal, engine
from backend.app.main import app
from backend.app.models import Task
from backend.app.models_clinical import LabRequest
from backend.app.seed import seed
from backend.app.common import uid
from backend.tests import test_labclear_gateway_pg as fixtures

ROOT = Path(__file__).resolve().parents[2]
LABCLEAR = ROOT.parent / "LabClear"
BASE = fixtures.BASE


@pytest.fixture(scope="module", autouse=True)
def explicit_seed():
    assert engine.url.database == "his_test"
    with SessionLocal.begin() as db:
        seed(db, os.environ["HIS_SEED_PASSWORD"])


@pytest.fixture(scope="module")
def actual_receiver(tmp_path_factory):
    python = LABCLEAR / ".venv/Scripts/python.exe"
    assert python.is_file(), "Explicit local LabClear test environment is required"
    state = tmp_path_factory.mktemp("carebalance-real-receiver")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    key = "synthetic-cross-app-receiver-key-not-used-in-runtime"
    environment = {name: value for name, value in os.environ.items() if name.lower() in
                   {"systemroot", "windir", "path", "pathext", "temp", "tmp", "userprofile", "localappdata", "appdata", "comspec", "home"}}
    environment.update(HIS_CAREBALANCE_TEST_RECEIVER="isolated-synthetic-only", HIS_CAREBALANCE_TEST_CONNECTOR_KEY=key)
    command = [str(python), str(ROOT / "scripts/carebalance_receiver_fixture.py"),
               "--labclear-root", str(LABCLEAR), "--state-root", str(state), "--port", str(port)]
    log_path = state.parent / (state.name + "-process.log")
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=state, env=environment, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 20
            with httpx.Client(trust_env=False, timeout=0.5) as probe_client:
                while time.monotonic() < deadline:
                    assert process.poll() is None, log_path.read_text(encoding="utf-8")
                    try:
                        response = probe_client.get(f"http://127.0.0.1:{port}/__test/ready")
                        if response.status_code == 200:
                            assert response.json()["fixture"] == "isolated-carebalance-connector"
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("Isolated LabClear HTTP receiver did not become ready")
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setenv("HIS_LABCLEAR_ENABLED", "true")
            monkeypatch.setenv("HIS_LABCLEAR_ORIGIN", f"http://127.0.0.1:{port}")
            monkeypatch.setenv("HIS_LABCLEAR_KEY", key)
            assert gateway.resolve_client not in app.dependency_overrides
            try:
                yield {"origin": f"http://127.0.0.1:{port}", "state": state}
            finally:
                monkeypatch.undo()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            assert process.poll() is not None


def test_real_http_import_human_correction_confirm_retry_and_readback(actual_receiver):
    client, body = fixtures.logged_in(), fixtures.source_fixture()
    imported, key = fixtures.imported(client, body)
    binding = imported["binding"]
    assert imported["receipt"]["state"] == "draft"
    assert len(binding["external_report_id"]) == 74
    confirm = fixtures.confirm_body(imported)
    confirmation_key = uid()
    path = BASE + "/bindings/" + binding["id"]
    response = client.post(path + "/confirm", json=confirm, headers={"Idempotency-Key": confirmation_key})
    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed["receipt"]["fields"][0]["value"] == "43"
    assert confirmed["receipt"]["fields"][0]["status"] == "high"
    assert confirmed["receipt"]["review"]["corrected_source_indices"] == [0]
    retry = client.post(path + "/confirm", json=confirm, headers={"Idempotency-Key": confirmation_key})
    assert retry.status_code == 200 and retry.json() == confirmed
    read = client.post(path + "/read")
    assert read.status_code == 200 and read.json()["receipt"] == confirmed["receipt"]
    with SessionLocal() as db:
        source = db.get(LabRequest, body["source_id"])
        assert (source.result_value, source.version, source.status) == ("42", 5, "released")
        assert db.get(Task, body["task_id"]).status == "open"
    if actual_receiver.get("storage") != "postgresql":
        assert (actual_receiver["state"] / "receiver.sqlite3").is_file()


def test_real_http_binding_scope_and_service_auth_remain_closed(actual_receiver):
    client, body = fixtures.logged_in(), fixtures.source_fixture()
    imported, _ = fixtures.imported(client, body)
    path = BASE + "/bindings/" + imported["binding"]["id"]
    assert fixtures.logged_in().post(path + "/read").status_code == 404
    assert fixtures.logged_in("laboratory").post(path + "/read").status_code == 404
    forged = {**body, "patient_id": "patient-002"}
    assert client.post(BASE + "/import", json=forged, headers={"Idempotency-Key": uid()}).status_code == 404
    with httpx.Client(trust_env=False, timeout=2) as service_client:
        denied = service_client.post(actual_receiver["origin"] + "/api/connector/reports/import", json={"context": {}})
        assert denied.status_code == 401
        assert service_client.get(actual_receiver["origin"] + "/api/business/reports").status_code == 404
