"""Run with LabClear's offline_check launcher and its isolated dependencies.

This tests the real HIS sender against the real LabClear ASGI receiver. It does
not exercise HIS PostgreSQL authorization or establish public deployment proof.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import httpx
import pytest

receiver_spec = importlib.util.find_spec("services")
if (receiver_spec is None or not receiver_spec.origin
        or not Path(receiver_spec.origin).parent.joinpath("carebalance_reports.py").is_file()):
    pytest.skip("Run this cross-application suite with LabClear scripts/offline_check.py", allow_module_level=True)

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.integration_clients import ConnectorConfig, ConnectorRejected, LabClearClient
from backend.app.integration_protocol import LaunchContext
from main import app
from services import business_store as db, carebalance_reports as reports


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    monkeypatch.setenv("BUSINESS_DB_PATH", str(tmp_path / "interop.sqlite3"))
    monkeypatch.setenv("BUSINESS_DATA_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("CAREBALANCE_CONNECTOR_ENABLED", "true")
    key = b"synthetic-interop-only-never-runtime-key" * 2
    monkeypatch.setenv("CAREBALANCE_CONNECTOR_KEY", key.decode())
    db._PURGED.clear()
    from routers import business
    for name in ("read_report", "save_read_report", "turn"):
        monkeypatch.setattr(business, name, lambda *a, **kw: pytest.fail("Forbidden OCR/model path"))
    with TestClient(app) as receiver:
        def send(request):
            result = receiver.post(request.url.path, content=request.content, headers=request.headers)
            return httpx.Response(result.status_code, headers=result.headers, content=result.content)
        yield LabClearClient(ConnectorConfig("carebalance-labclear", "http://127.0.0.1:18090", key),
                             transport=httpx.MockTransport(send))


def context():
    payload = {"protocol": "carebalance.connector.v1", "request_id": "request_interop_001",
               "audience": "carebalance-labclear", "binding_id": "binding_interop_001",
               "organization_id": "org-interop", "facility_id": "facility-interop", "actor_id": "actor-interop",
               "patient_id": "patient-interop", "encounter_id": "visit-interop", "task_id": "task-interop",
               "source": {"domain": "D10", "record_id": "lab-interop", "version": 2, "sha256": "a" * 64},
               "purpose": "lab-value-review",
               "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
               "lab_values": [{"analyte": "ALT", "printed_value": " 42 ", "unit": "U/L", "reference_range": "0-40"},
                              {"analyte": "Qualitative", "printed_value": "Negative", "unit": None, "reference_range": None}]}
    return LaunchContext.model_validate_json(json.dumps(payload))


def test_actual_sender_receiver_import_review_readback(bridge):
    ctx = context()
    draft = bridge.import_report(ctx)
    assert draft["state"] == "draft" and draft["review"] is None
    assert len(draft["report_id"]) == 74
    assert bridge.import_report(ctx) == draft
    assert bridge.read_report(ctx, draft["report_id"]) == draft
    fields = deepcopy(draft["fields"])
    fields[0]["value"] = "43"
    confirmed = bridge.confirm_report(ctx, draft["report_id"], fields=fields, same_person_confirmed=True)
    assert confirmed["state"] == "confirmed"
    assert confirmed["review"]["corrected_source_indices"] == [0]
    assert confirmed["fields"][0]["value"] == "43"
    assert confirmed["fields"][0]["status"] == "high"
    assert confirmed["fields"][1]["status"] == "unknown"
    assert bridge.confirm_report(ctx, draft["report_id"], fields=fields, same_person_confirmed=True) == confirmed
    assert bridge.read_report(ctx, draft["report_id"]) == confirmed
    with db.transaction() as tx:
        original = tx.own(reports.source_id(ctx), reports.owner_for(ctx), "carebalance_source")
        assert original["data"]["cells"][0]["printed_value"] == " 42 "
        assert original["data"]["cells"][1]["unit"] is None
        assert tx.find("report", reports.owner_for(ctx)) == []


@pytest.mark.parametrize("field", ["actor_id", "patient_id", "organization_id", "facility_id", "encounter_id", "task_id"])
def test_actual_wire_foreign_context_denied(bridge, field):
    ctx = context()
    draft = bridge.import_report(ctx)
    changed = ctx.model_copy(update={field: "foreign-subject"})
    with pytest.raises(ConnectorRejected) as error:
        bridge.read_report(changed, draft["report_id"])
    assert error.value.status_code in {404, 409}


def test_actual_wire_semantic_idempotency_conflict(bridge):
    ctx = context()
    bridge.import_report(ctx)
    changed = ctx.model_copy(update={"lab_values": (ctx.lab_values[0].model_copy(update={"printed_value": "tampered"}), ctx.lab_values[1])})
    with pytest.raises(ConnectorRejected) as error:
        bridge.import_report(changed)
    assert error.value.status_code == 409


def test_actual_his_receiver_protocol_byte_parity():
    his_protocol = Path(__file__).resolve().parents[1] / "app/integration_protocol.py"
    import services.carebalance_protocol as receiver_protocol
    assert hashlib.sha256(his_protocol.read_bytes()).digest() == hashlib.sha256(Path(receiver_protocol.__file__).read_bytes()).digest()
