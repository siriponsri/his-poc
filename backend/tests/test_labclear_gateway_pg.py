"""Actual disposable PostgreSQL tests with an authenticated synthetic receiver double."""
import os

assert os.environ.get("HIS_TEST_DATABASE_URL") and os.environ["HIS_TEST_DATABASE_URL"] == os.environ.get("DATABASE_URL"), "Disposable PostgreSQL wrapper required"

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import threading
import time

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from backend.app import integrations as gateway
from backend.app.common import digest, text_hash, uid, utcnow
from backend.app.db import SessionLocal, engine
from backend.app.integration_clients import ConnectorConfig, LabClearClient
from backend.app.integration_protocol import verify_request
from backend.app.main import app
from backend.app.models import CareAssignment, ClinicalOrder, Membership, SessionRecord, Task
from backend.app.models_clinical import LabRequest
from backend.app.models_integrations import ConnectorAttempt, ConnectorBinding, ConnectorExchange
from backend.app.seed import seed

BASE = "/api/v2/integrations/labclear"
KEY = b"isolated-gateway-receiver-test-key-only"


@pytest.fixture(scope="module", autouse=True)
def explicit_isolated_seed():
    assert engine.url.database == "his_test"
    with SessionLocal.begin() as db:
        seed(db, os.environ["HIS_SEED_PASSWORD"])


def logged_in(username="clinician"):
    client = TestClient(app)
    response = client.post("/api/v2/auth/login", json={"username": username, "password": os.environ["HIS_SEED_PASSWORD"]})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


def source_fixture(patient_id="patient-001", encounter_id="encounter-001"):
    with SessionLocal.begin() as db:
        old = Task(id=uid(), organization_id="org-demo", facility_id="facility-demo", patient_id=patient_id,
                   encounter_id=encounter_id, domain="D10", kind="lab", title="Completed original lab order", status="completed")
        review = Task(id=uid(), organization_id="org-demo", facility_id="facility-demo", patient_id=patient_id,
                      encounter_id=encounter_id, domain="D10", kind="labclear_review", title="Explicit LabClear review", status="open")
        db.add_all([old, review]); db.flush()
        order = ClinicalOrder(id=uid(), organization_id="org-demo", facility_id="facility-demo", patient_id=patient_id,
            encounter_id=encounter_id, task_id=old.id, requester_id="user-clinician", kind="lab", code="SYN-ALT",
            label="Synthetic ALT", status="fulfilled", quantity=1, unit="test")
        db.add(order); db.flush()
        source = LabRequest(id=uid(), organization_id="org-demo", facility_id="facility-demo", patient_id=patient_id,
            encounter_id=encounter_id, created_by="user-laboratory", status="released", version=5,
            order_id=order.id, order_version=1, analyte="ALT", specimen_type="serum", result_value="42", unit="U/L", reference_range="0-40")
        db.add(source); db.flush()
        return {"patient_id": source.patient_id, "encounter_id": source.encounter_id, "task_id": review.id,
                "source_id": source.id, "source_version": source.version}


class ReceiverDouble:
    """Validates actual HMAC bytes and returns the frozen receipt schema. No socket."""
    def __init__(self):
        self.records = {}
        self.calls = []
        self.hook = None
        self.fail_after_save = False
        self.return_snapshot_before_hook = False

    def __call__(self, request):
        assert engine.pool.checkedout() == 0, "HIS held a database connection across receiver HTTP"
        verify_request(KEY, method=request.method, path=request.url.path,
            timestamp=int(request.headers["X-CareBalance-Timestamp"]), nonce=request.headers["X-CareBalance-Nonce"],
            audience=request.headers["X-CareBalance-Audience"], body=request.content,
            signature=request.headers["X-CareBalance-Signature"], expected_audience="carebalance-labclear", now=int(time.time()))
        payload = json.loads(request.content)
        context = payload["context"]
        self.calls.append((request.url.path, deepcopy(context)))
        id = context["binding_id"]
        if request.url.path.endswith("/import") and id not in self.records:
            self.records[id] = {"protocol": context["protocol"], "report_id": "cb_report_" + digest(id), "state": "draft",
                "source": context["source"], "snapshot_sha256": digest(context["lab_values"]), "review": None,
                "fields": [{"source_index": i, "name": row["analyte"].strip(), "value": row["printed_value"].strip(),
                    "unit": (row["unit"] or "").strip(), "reference": (row["reference_range"] or "").strip(), "printed_flag": ""}
                    for i, row in enumerate(context["lab_values"])]}
        if request.url.path.endswith("/confirm"):
            row = self.records[id]
            row["state"] = "confirmed"
            row["fields"] = [{**field, "id": "r" + str(i + 1), "status": "high"} for i, field in enumerate(payload["fields"])]
            row["review"] = {"revision": 1, "sha256": digest(row["fields"]), "reviewer_id": context["actor_id"],
                "confirmed_at": time.time(), "same_person_confirmed": True, "source_revision": context["source"]["version"],
                "source_sha256": context["source"]["sha256"], "corrected_source_indices": [0]}
        snapshot = deepcopy(self.records[id])
        if self.hook:
            self.hook(context)
        if self.fail_after_save:
            self.fail_after_save = False
            return httpx.Response(503, json={"private": "never forward this upstream error"})
        return httpx.Response(200, json=snapshot if self.return_snapshot_before_hook else self.records[id])


@pytest.fixture
def receiver():
    double = ReceiverDouble()
    client = LabClearClient(ConnectorConfig("carebalance-labclear", "http://127.0.0.1:18090", KEY), transport=httpx.MockTransport(double))
    app.dependency_overrides[gateway.resolve_client] = lambda: client
    try:
        yield double
    finally:
        app.dependency_overrides.pop(gateway.resolve_client, None)


def imported(client, body, key=None):
    key = key or uid()
    response = client.post(BASE + "/import", json=body, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    return response.json(), key


def confirm_body(result):
    return {"fields": [{"source_index": 0, "name": "ALT", "value": "43", "unit": "U/L", "reference": "0-40", "printed_flag": ""}],
            "same_person_confirmed": True, "source_version": result["binding"]["source_version"],
            "source_sha256": result["binding"]["source_sha256"]}


def test_migration_ready_import_review_read_and_his_unchanged(receiver):
    client, body = logged_in(), source_fixture()
    assert client.get("/ready").json()["migration"] == "0003_carebalance_integrations"
    result, key = imported(client, body)
    id = result["binding"]["id"]
    assert len(result["binding"]["external_report_id"]) == 74
    assert client.get(BASE + "/bindings", params={"patient_id": body["patient_id"], "encounter_id": body["encounter_id"]}).json()["items"][0]["id"] == id
    confirm_key = uid()
    reviewed = client.post(BASE + "/bindings/" + id + "/confirm", json=confirm_body(result), headers={"Idempotency-Key": confirm_key})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["receipt"]["fields"][0]["value"] == "43"
    repeated = client.post(BASE + "/bindings/" + id + "/confirm", json=confirm_body(result), headers={"Idempotency-Key": confirm_key})
    assert repeated.status_code == 200 and repeated.json() == reviewed.json()
    changed = confirm_body(result); changed["fields"][0]["value"] = "44"
    assert client.post(BASE + "/bindings/" + id + "/confirm", json=changed, headers={"Idempotency-Key": confirm_key}).status_code == 409
    assert client.post(BASE + "/bindings/" + id + "/confirm", json=changed, headers={"Idempotency-Key": uid()}).status_code == 409
    read = client.post(BASE + "/bindings/" + id + "/read")
    assert read.status_code == 200 and read.json()["receipt"]["state"] == "confirmed"
    with SessionLocal() as db:
        source = db.get(LabRequest, body["source_id"])
        assert (source.result_value, source.version, source.status) == ("42", 5, "released")
        assert db.get(Task, body["task_id"]).status == "open"
        assert db.scalar(select(func.count()).select_from(ConnectorExchange).where(ConnectorExchange.attempt_id.in_(select(ConnectorAttempt.id).where(ConnectorAttempt.binding_id == id)))) == 3


def test_timeout_unknown_retries_same_receiver_request_without_duplicate(receiver):
    client, body, key = logged_in(), source_fixture(), uid()
    receiver.fail_after_save = True
    unknown = client.post(BASE + "/import", json=body, headers={"Idempotency-Key": key})
    assert unknown.status_code == 202 and unknown.json()["outcome"] == "unknown"
    assert "private" not in unknown.text
    restored = TestClient(app)
    restored.cookies.update(client.cookies)
    restored.headers["X-CSRF-Token"] = client.headers["X-CSRF-Token"]
    recovery = restored.post(BASE + "/bindings/" + unknown.json()["binding"]["id"] + "/recover")
    assert recovery.status_code == 200, recovery.text
    pending = recovery.json()["pending"]
    assert recovery.json()["retry_allowed"] is True
    assert pending["kind"] == "import" and pending["key"] == key and pending["body"] == body
    assert pending["path"] == "integrations/labclear/import" and pending["method"] == "POST"
    assert len(receiver.calls) == 1  # Recovery is read-only; no automatic resend.
    result, _ = imported(client, body, key)
    assert len(receiver.records) == 1 and len(receiver.calls) == 2
    assert receiver.calls[0][1]["request_id"] == receiver.calls[1][1]["request_id"]
    assert receiver.calls[0][1]["binding_id"] == receiver.calls[1][1]["binding_id"]
    retry = client.post(BASE + "/import", json=body, headers={"Idempotency-Key": key})
    assert retry.status_code == 200 and retry.json() == result
    assert len(receiver.calls) == 2
    changed = {**body, "task_id": source_fixture()["task_id"]}
    assert client.post(BASE + "/import", json=changed, headers={"Idempotency-Key": key}).status_code == 409


def test_unknown_confirmation_command_recovers_after_refresh_with_scope_fences(receiver):
    client, body = logged_in(), source_fixture()
    result, _ = imported(client, body)
    path = BASE + "/bindings/" + result["binding"]["id"]
    key, payload = uid(), confirm_body(result)
    receiver.fail_after_save = True
    response = client.post(path + "/confirm", json=payload, headers={"Idempotency-Key": key})
    assert response.status_code == 202 and response.json()["retry_same_key"] is True
    recovery = client.post(path + "/recover")
    assert recovery.status_code == 200
    pending = recovery.json()["pending"]
    assert pending["kind"] == "confirm" and pending["key"] == key and pending["body"] == payload
    assert pending["path"] == "integrations/labclear/bindings/" + result["binding"]["id"] + "/confirm"
    assert len(receiver.calls) == 2
    assert logged_in().post(path + "/recover").status_code == 404
    with SessionLocal.begin() as db:
        task = db.get(Task, body["task_id"]); task.status = "completed"; task.version += 1
    denied = client.post(path + "/recover")
    assert denied.status_code == 409 and "fields" not in denied.text
    assert len(receiver.calls) == 2


def test_actor_session_csrf_scope_and_stale_source_denials(receiver):
    client, body = logged_in(), source_fixture()
    result, _ = imported(client, body)
    path = BASE + "/bindings/" + result["binding"]["id"]
    for other in [logged_in("laboratory"), logged_in("clinician")]:
        assert other.post(path + "/read").status_code == 404
    csrf = client.headers.pop("X-CSRF-Token")
    assert client.post(path + "/read").status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    for changed in [{**body, "patient_id": "patient-002"}, {**body, "encounter_id": "encounter-002"}, {**body, "source_version": 4}]:
        assert client.post(BASE + "/import", json=changed, headers={"Idempotency-Key": uid()}).status_code in {404, 409}
    with SessionLocal.begin() as db:
        source = db.get(LabRequest, body["source_id"]); source.version += 1; source.result_value = "99"
    assert client.post(path + "/read").status_code == 409
    assert len(receiver.calls) == 1


def test_foreign_task_and_source_are_filtered_before_row_lock(receiver):
    client, own = logged_in(), source_fixture()
    foreign = source_fixture("patient-002", "encounter-002")

    def limited_db():
        with SessionLocal() as db:
            db.execute(text("SET LOCAL lock_timeout = '150ms'"))
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    app.dependency_overrides[gateway.get_db] = limited_db
    try:
        with SessionLocal.begin() as locker:
            locker.get(Task, foreign["task_id"], with_for_update=True)
            locker.get(LabRequest, foreign["source_id"], with_for_update=True)
            # An ID-only FOR UPDATE would wait on the locked foreign row and
            # hit lock_timeout (503), instead of returning a scoped 404.
            for field in ("task_id", "source_id"):
                response = client.post(BASE + "/import", json={**own, field: foreign[field]},
                                       headers={"Idempotency-Key": uid()})
                assert response.status_code == 404, (field, response.status_code, response.text)
        assert receiver.calls == []
    finally:
        app.dependency_overrides.pop(gateway.get_db, None)


@pytest.mark.parametrize("mutation,status", [("session", 401), ("membership", 401), ("source", 409), ("task", 409), ("assignment", 404)])
def test_inflight_authorization_or_source_change_quarantines_actual_receipt(receiver, mutation, status):
    client, body = logged_in(), source_fixture()
    session_hash = text_hash(client.cookies.get("his_session"))
    def invalidate(context):
        with SessionLocal.begin() as db:
            if mutation == "session":
                db.scalar(select(SessionRecord).where(SessionRecord.token_hash == session_hash)).revoked_at = utcnow()
            elif mutation == "membership":
                db.get(Membership, "membership-clinician").active = False
            elif mutation == "source":
                source = db.get(LabRequest, body["source_id"]); source.version += 1; source.result_value = "99"
            elif mutation == "task":
                task = db.get(Task, body["task_id"]); task.status = "completed"; task.version += 1
            else:
                db.get(CareAssignment, ("user-clinician", "patient-001")).active = False
    receiver.hook = invalidate
    try:
        response = client.post(BASE + "/import", json=body, headers={"Idempotency-Key": uid()})
        assert response.status_code == status, response.text
        assert "fields" not in response.text and "42" not in response.text
        with SessionLocal() as db:
            binding = db.scalar(select(ConnectorBinding).where(ConnectorBinding.task_id == body["task_id"]))
            attempt = db.scalar(select(ConnectorAttempt).where(ConnectorAttempt.binding_id == binding.id))
            exchange = db.scalar(select(ConnectorExchange).where(ConnectorExchange.attempt_id == attempt.id))
            assert (binding.state, attempt.status, exchange.outcome, exchange.quarantined) == ("quarantined", "quarantined", "succeeded", True)
            assert exchange.receipt["fields"][0]["value"] == "42"
    finally:
        if mutation == "assignment":
            with SessionLocal.begin() as db:
                db.get(CareAssignment, ("user-clinician", "patient-001")).active = True
        if mutation == "membership":
            with SessionLocal.begin() as db:
                db.get(Membership, "membership-clinician").active = True


def test_old_read_draft_response_cannot_regress_confirmed_binding(receiver):
    client, body = logged_in(), source_fixture()
    result, _ = imported(client, body)
    id = result["binding"]["id"]
    receiver.return_snapshot_before_hook = True
    def confirm_during_import(context):
        receiver.hook = None
        response = client.post(BASE + "/bindings/" + id + "/confirm", json=confirm_body(result), headers={"Idempotency-Key": uid()})
        assert response.status_code == 200, response.text
    receiver.hook = confirm_during_import
    response = client.post(BASE + "/bindings/" + id + "/read")
    assert response.status_code == 409 and response.json()["detail"]["code"] == "CONNECTOR_RECEIPT_STALE"
    with SessionLocal() as db:
        assert db.get(ConnectorBinding, id).state == "confirmed"
        assert db.scalar(select(func.count()).select_from(ConnectorExchange).where(ConnectorExchange.quarantined.is_(True),
            ConnectorExchange.quarantine_reason == "CONNECTOR_RECEIPT_STALE")) == 1
    assert client.post(BASE + "/bindings/" + id + "/read").json()["receipt"]["state"] == "confirmed"


def test_unresolved_mutation_requires_exact_command_recovery(receiver):
    client, body, key = logged_in(), source_fixture(), uid()
    receiver.fail_after_save = True
    pending = client.post(BASE + "/import", json=body, headers={"Idempotency-Key": key})
    assert pending.status_code == 202
    binding_id = pending.json()["binding"]["id"]
    denied = client.post(BASE + "/import", json=body, headers={"Idempotency-Key": uid()})
    assert denied.status_code == 409
    assert denied.json()["detail"] == {"code": "CONNECTOR_PENDING_RECOVERY_REQUIRED", "binding_id": binding_id}
    assert len(receiver.calls) == 1
    result, _ = imported(client, body, key)
    receiver.fail_after_save = True
    confirmation = confirm_body(result)
    confirm_key = uid()
    path = BASE + "/bindings/" + binding_id
    assert client.post(path + "/confirm", json=confirmation, headers={"Idempotency-Key": confirm_key}).status_code == 202
    for operation, payload in [("/import", body), ("/bindings/" + binding_id + "/confirm", confirmation)]:
        denied = client.post(BASE + operation, json=payload, headers={"Idempotency-Key": uid()})
        assert denied.status_code == 409 and denied.json()["detail"]["code"] == "CONNECTOR_PENDING_RECOVERY_REQUIRED"
    assert len(receiver.calls) == 3
    assert client.post(path + "/recover").json()["pending"]["key"] == confirm_key


def test_released_task_confirmation_and_mapping_gates_precede_http(receiver):
    client, body = logged_in(), source_fixture()
    result, _ = imported(client, body)
    path = BASE + "/bindings/" + result["binding"]["id"]
    for change, expected in [("person", 422), ("mapping", 422), ("version", 409), ("hash", 409)]:
        data = confirm_body(result)
        if change == "person": data["same_person_confirmed"] = False
        if change == "mapping": data["fields"][0]["source_index"] = 1
        if change == "version": data["source_version"] = 4
        if change == "hash": data["source_sha256"] = "b" * 64
        assert client.post(path + "/confirm", json=data, headers={"Idempotency-Key": uid()}).status_code == expected
    with SessionLocal.begin() as db:
        task = db.get(Task, body["task_id"]); task.status = "completed"; task.version += 1
    assert client.post(path + "/confirm", json=confirm_body(result), headers={"Idempotency-Key": uid()}).status_code == 409
    assert client.post(path + "/read").status_code == 200
    assert len(receiver.calls) == 2  # import and the explicitly allowed historical read


def test_live_lease_one_http_call_under_concurrent_retry(receiver):
    client, body, key = logged_in(), source_fixture(), uid()
    entered, release = threading.Event(), threading.Event()
    def wait_for_retry(context):
        entered.set()
        assert release.wait(10), "retry did not release the receiver fixture"
    receiver.hook = wait_for_retry
    def call():
        return client.post(BASE + "/import", json=body, headers={"Idempotency-Key": key})
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(call)
        assert entered.wait(10)
        try:
            second = call()
            assert second.status_code == 202 and second.json()["outcome"] == "running"
        finally:
            release.set()
        first = future.result(timeout=15)
    assert first.status_code == 200, first.text
    assert len(receiver.calls) == 1


def test_pg_guards_preserve_source_attempt_and_completed_exchange(receiver):
    result, _ = imported(logged_in(), source_fixture())
    id = result["binding"]["id"]
    with SessionLocal() as db:
        attempt = db.scalar(select(ConnectorAttempt).where(ConnectorAttempt.binding_id == id))
        exchange = db.scalar(select(ConnectorExchange).where(ConnectorExchange.attempt_id == attempt.id))
        attempt_id, exchange_id = attempt.id, exchange.id
    statements = [("UPDATE connector_bindings SET source_hash = :value WHERE id = :id", id, "b" * 64),
                  ("UPDATE connector_attempts SET request_hash = :value WHERE id = :id", attempt_id, "b" * 64),
                  ("UPDATE connector_exchanges SET outcome = :value WHERE id = :id", exchange_id, "unknown")]
    for sql, row_id, value in statements:
        with pytest.raises(DBAPIError), SessionLocal.begin() as db:
            db.execute(text(sql), {"id": row_id, "value": value})
