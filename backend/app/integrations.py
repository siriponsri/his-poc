"""HIS-authorized LabClear gateway: reserve, close transaction, send, recheck."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import hashlib

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text

from .auth import current_actor, revalidate_actor, require_domain, scoped_encounter, scoped_patient
from .common import audit, authorization_hash, digest, uid, utcnow
from .task_identity import task_source_version
from .db import get_db, SessionLocal
from .integration_clients import ConnectorConfig, ConnectorOutcomeUnknown, ConnectorRejected, ConnectorUnavailable, LabClearClient
from .integration_protocol import LabValue, LaunchContext
from .models import AuditEvent, ClinicalOrder, Task
from .models_clinical import LabRequest
from .models_integrations import ConnectorAttempt, ConnectorBinding, ConnectorExchange

router = APIRouter(prefix="/integrations/labclear", tags=["specialist integration"])
LEASE_SECONDS = 30
CLOSED = {"closed", "completed", "discharged", "cancelled"}


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ImportInput(Input):
    patient_id: str = Field(min_length=1, max_length=64)
    encounter_id: str = Field(min_length=1, max_length=64)
    task_id: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=64)
    source_version: int = Field(ge=1)


class ReviewedField(Input):
    source_index: int = Field(ge=0, le=59)
    name: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=150)
    unit: str = Field(max_length=60)
    reference: str = Field(max_length=150)
    printed_flag: str = Field(max_length=25)


class ConfirmInput(Input):
    fields: list[ReviewedField] = Field(min_length=1, max_length=60)
    same_person_confirmed: bool
    source_version: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def failure(code, status=409):
    raise HTTPException(status, detail={"code": code})


def resolve_client():
    try:
        return LabClearClient(ConnectorConfig.from_environment("carebalance-labclear"))
    except ConnectorUnavailable:
        failure("LABCLEAR_CONNECTOR_UNAVAILABLE", 503)


def _lock(db, value):
    key = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def lab_snapshot(source: LabRequest) -> dict:
    names = ("id", "organization_id", "facility_id", "patient_id", "encounter_id", "order_id", "order_version",
             "version", "status", "analyte", "specimen_type", "accession", "result_value", "unit", "reference_range")
    return {"schema": "carebalance.his-lab-source.v1", "domain": "D10", **{name: getattr(source, name) for name in names}}


def lab_values(snapshot: dict) -> list[dict]:
    if (not isinstance(snapshot["analyte"], str) or not snapshot["analyte"].strip()
            or not isinstance(snapshot["result_value"], str) or not snapshot["result_value"].strip()
            or len(snapshot["analyte"]) > 100 or len(snapshot["result_value"]) > 150):
        failure("LABCLEAR_SOURCE_CELL_UNSUPPORTED", 422)
    return [{"analyte": snapshot["analyte"], "printed_value": snapshot["result_value"],
             "unit": snapshot["unit"], "reference_range": snapshot["reference_range"]}]


def _authorize_source(db, actor, patient_id, encounter_id, task_id, source_id, *, write, version=None):
    revalidate_actor(db, actor)
    require_domain(actor, "D10", True)
    scoped_patient(db, actor, patient_id, True)
    encounter = scoped_encounter(db, actor, encounter_id, True)
    if encounter.patient_id != patient_id:
        failure("CONNECTOR_ENCOUNTER_PATIENT_MISMATCH", 404)
    expected = (actor.organization_id, actor.facility_id, patient_id, encounter_id)
    task = db.scalar(select(Task).where(Task.id == task_id, Task.organization_id == actor.organization_id,
        Task.facility_id == actor.facility_id, Task.patient_id == patient_id, Task.encounter_id == encounter_id)
        .with_for_update().execution_options(populate_existing=True))
    source = db.scalar(select(LabRequest).where(LabRequest.id == source_id,
        LabRequest.organization_id == actor.organization_id, LabRequest.facility_id == actor.facility_id,
        LabRequest.patient_id == patient_id, LabRequest.encounter_id == encounter_id)
        .with_for_update().execution_options(populate_existing=True))
    if any(row is None or (row.organization_id, row.facility_id, row.patient_id, row.encounter_id) != expected
           for row in (task, source)):
        failure("CONNECTOR_CONTEXT_NOT_FOUND", 404)
    if task.domain != "D10" or task.kind != "labclear_review":
        failure("LABCLEAR_REVIEW_TASK_REQUIRED", 422)
    if write and (task.status not in {"open", "in_progress"} or encounter.status in CLOSED):
        failure("CONNECTOR_TARGET_CLOSED")
    if not write and task.status not in {"open", "in_progress", "completed"}:
        failure("CONNECTOR_REVIEW_TASK_UNAVAILABLE")
    order = db.scalar(select(ClinicalOrder).where(ClinicalOrder.id == source.order_id).execution_options(populate_existing=True))
    if not order or (order.organization_id, order.facility_id, order.patient_id, order.encounter_id) != expected:
        failure("CONNECTOR_ORDER_SCOPE_MISMATCH", 404)
    if order.kind != "lab":
        failure("CONNECTOR_LAB_ORDER_REQUIRED")
    if source.status not in {"released", "corrected"}:
        failure("LABCLEAR_RELEASED_SOURCE_REQUIRED")
    if version is not None and source.version != version:
        failure("CONNECTOR_SOURCE_STALE")
    snapshot = lab_snapshot(source)
    return source, task, encounter, snapshot


def _owned_binding(db, actor, id, *, write=False):
    # Revalidate before evaluating the binding so a revoked session never exposes it.
    revalidate_actor(db, actor)
    require_domain(actor, "D10", True)
    binding = db.scalar(select(ConnectorBinding).where(ConnectorBinding.id == id,
        ConnectorBinding.actor_id == actor.user_id, ConnectorBinding.session_id == actor.session_id,
        ConnectorBinding.organization_id == actor.organization_id, ConnectorBinding.facility_id == actor.facility_id,
        ConnectorBinding.connector == "labclear").with_for_update().execution_options(populate_existing=True))
    if not binding:
        failure("CONNECTOR_BINDING_NOT_FOUND", 404)
    source, task, encounter, snapshot = _authorize_source(db, actor, binding.patient_id, binding.encounter_id,
        binding.task_id, binding.source_id, write=write, version=binding.source_version)
    if snapshot != binding.source_snapshot or digest(snapshot) != binding.source_hash:
        failure("CONNECTOR_SOURCE_STALE")
    return binding, task, encounter


def binding_dto(binding):
    return {"id": binding.id, "connector": binding.connector, "patient_id": binding.patient_id,
            "encounter_id": binding.encounter_id, "task_id": binding.task_id, "source_id": binding.source_id,
            "source_version": binding.source_version, "source_sha256": binding.source_hash,
            "external_report_id": binding.external_report_id, "state": binding.state,
            "created_at": binding.created_at.isoformat()}


def _pending(binding, attempt):
    return JSONResponse(status_code=202, content={"binding": binding_dto(binding), "attempt_id": attempt.id,
        "outcome": attempt.status, "receipt": None, "retry_same_key": attempt.operation != "read"})


def context_for(binding, request_id):
    return LaunchContext(protocol="carebalance.connector.v1", request_id=request_id,
        audience="carebalance-labclear", binding_id=binding.id, organization_id=binding.organization_id,
        facility_id=binding.facility_id, actor_id=binding.actor_id, patient_id=binding.patient_id,
        encounter_id=binding.encounter_id, task_id=binding.task_id,
        source={"domain": "D10", "record_id": binding.source_id, "version": binding.source_version, "sha256": binding.source_hash},
        purpose="lab-value-review", expires_at=utcnow() + timedelta(seconds=90),
        lab_values=tuple(LabValue(**value) for value in binding.lab_values))


@dataclass(frozen=True)
class Reservation:
    binding_id: str
    attempt_id: str
    exchange_id: str
    context: LaunchContext
    operation: str
    fields: list[dict] | None
    external_report_id: str | None


def _reserve_attempt(db, actor, binding, task, encounter, operation, key, payload):
    if not key or len(key) > 120:
        failure("IDEMPOTENCY_KEY_REQUIRED", 400)
    _lock(db, "his-connector-key:" + actor.user_id + ":" + actor.session_id + ":" + key)
    request_hash = digest({"binding_id": binding.id, "operation": operation, "payload": payload})
    auth_hash = authorization_hash(actor)
    prior = db.scalar(select(ConnectorAttempt).where(ConnectorAttempt.actor_id == actor.user_id,
        ConnectorAttempt.session_id == actor.session_id, ConnectorAttempt.operation_key == key).with_for_update())
    if prior:
        if (prior.binding_id != binding.id or prior.operation != operation or prior.request_hash != request_hash
                or prior.authorization_hash != auth_hash):
            failure("IDEMPOTENCY_CONFLICT")
        if prior.status == "succeeded":
            return deepcopy(prior.response)
        if prior.status == "quarantined":
            failure(prior.error_code or "CONNECTOR_ATTEMPT_QUARANTINED")
        if prior.status == "rejected":
            failure(prior.error_code or "CONNECTOR_ATTEMPT_REJECTED", 503 if prior.error_code == "LABCLEAR_CONNECTOR_UNAVAILABLE" else 502)
        if prior.status == "running" and prior.lease_expires_at > utcnow():
            return _pending(binding, prior)
        attempt = prior
    else:
        if operation in {"import", "confirm"}:
            unresolved = db.scalar(select(ConnectorAttempt).where(ConnectorAttempt.binding_id == binding.id,
                ConnectorAttempt.actor_id == actor.user_id, ConnectorAttempt.session_id == actor.session_id,
                ConnectorAttempt.operation.in_(["import", "confirm"]),
                ConnectorAttempt.status.in_(["running", "unknown"]))
                .with_for_update().limit(1))
            if unresolved is not None:
                raise HTTPException(409, detail={"code": "CONNECTOR_PENDING_RECOVERY_REQUIRED", "binding_id": binding.id})
        if operation == "confirm" and binding.state == "confirmed":
            failure("LABCLEAR_REVIEW_ALREADY_CONFIRMED")
        attempt = ConnectorAttempt(id=uid(), binding_id=binding.id, actor_id=actor.user_id, session_id=actor.session_id,
            operation=operation, operation_key=key, request_id=uid(), request_hash=request_hash,
            authorization_hash=auth_hash, payload=payload)
        db.add(attempt)
    exchange_id = uid()
    attempt.status = "running"
    attempt.lease_id = exchange_id
    attempt.lease_expires_at = utcnow() + timedelta(seconds=LEASE_SECONDS)
    attempt.error_code = None
    attempt.completed_at = None
    db.flush()
    exchange = ConnectorExchange(id=exchange_id, attempt_id=attempt.id,
        context_snapshot={"authorization_hash": auth_hash, "task_version": task_source_version(db,task),
                          "encounter_version": encounter.version}, outcome="running")
    db.add(exchange)
    context = context_for(binding, attempt.request_id)
    reservation = Reservation(binding.id, attempt.id, exchange_id, context, operation,
        payload.get("fields"), binding.external_report_id)
    audit(db, actor, "D10", binding.id, "labclear." + operation + ".reserved", {"attempt_id": attempt.id, "exchange_id": exchange_id})
    db.commit()
    db.close()
    return reservation


def _store_exchange(reservation, outcome, receipt, code):
    # This records an already-authorized outbound call's actual outcome even if
    # current clinical access was revoked while that call was in flight.
    with SessionLocal.begin() as db:
        exchange = db.get(ConnectorExchange, reservation.exchange_id, with_for_update=True)
        if not exchange or exchange.attempt_id != reservation.attempt_id or exchange.outcome != "running":
            failure("CONNECTOR_EXCHANGE_INCONSISTENT")
        exchange.outcome = outcome
        exchange.receipt = receipt
        exchange.error_code = code
        exchange.completed_at = utcnow()


def _quarantine(reservation, code):
    with SessionLocal.begin() as db:
        binding = db.get(ConnectorBinding, reservation.binding_id, with_for_update=True)
        attempt = db.get(ConnectorAttempt, reservation.attempt_id, with_for_update=True)
        exchange = db.get(ConnectorExchange, reservation.exchange_id, with_for_update=True)
        if exchange:
            exchange.quarantined = True
            exchange.quarantine_reason = code
        if attempt and attempt.lease_id == reservation.exchange_id:
            attempt.status = "quarantined"
            attempt.error_code = code
            attempt.completed_at = utcnow()
            if code != "CONNECTOR_RECEIPT_STALE":
                binding.state = "quarantined"
        if binding:
            db.add(AuditEvent(organization_id=binding.organization_id, facility_id=binding.facility_id,
                actor_id=binding.actor_id, domain="D10", entity_id=binding.id, action="labclear.outcome.quarantined",
                details={"attempt_id": reservation.attempt_id, "exchange_id": reservation.exchange_id, "code": code}))


def _execute(db, actor, client, reservation):
    if not isinstance(reservation, Reservation):
        return reservation
    try:
        if reservation.operation == "import":
            receipt = client.import_report(reservation.context)
        elif reservation.operation == "read":
            receipt = client.read_report(reservation.context, reservation.external_report_id)
        else:
            receipt = client.confirm_report(reservation.context, reservation.external_report_id,
                fields=reservation.fields, same_person_confirmed=True)
        outcome, code = "succeeded", None
    except ConnectorRejected:
        receipt, outcome, code = None, "rejected", "LABCLEAR_REQUEST_REJECTED"
    except ConnectorUnavailable:
        receipt, outcome, code = None, "rejected", "LABCLEAR_CONNECTOR_UNAVAILABLE"
    except Exception:
        receipt, outcome, code = None, "unknown", "LABCLEAR_OUTCOME_UNKNOWN"
    _store_exchange(reservation, outcome, receipt, code)
    try:
        binding, task, encounter = _owned_binding(db, actor, reservation.binding_id, write=reservation.operation != "read")
        attempt = db.get(ConnectorAttempt, reservation.attempt_id, with_for_update=True)
        exchange = db.get(ConnectorExchange, reservation.exchange_id)
        if attempt.lease_id != reservation.exchange_id:
            failure("CONNECTOR_LEASE_REPLACED")
        snapshot = exchange.context_snapshot
        if (authorization_hash(actor) != snapshot["authorization_hash"] or (reservation.operation != "read"
                and (task_source_version(db,task) != snapshot["task_version"] or encounter.version != snapshot["encounter_version"]))):
            failure("CONNECTOR_CONTEXT_CHANGED")
        if outcome == "succeeded" and binding.state == "confirmed" and receipt["state"] == "draft":
            failure("CONNECTOR_RECEIPT_STALE")
        attempt.status = outcome
        attempt.error_code = code
        attempt.completed_at = utcnow()
        if outcome == "succeeded":
            binding.external_report_id = receipt["report_id"]
            binding.state = receipt["state"]
            response = {"binding": binding_dto(binding), "attempt_id": attempt.id, "outcome": outcome, "receipt": receipt}
            attempt.response = response
        elif outcome == "unknown":
            if binding.state not in {"draft", "confirmed"}:
                binding.state = "unknown"
            response = _pending(binding, attempt)
        else:
            response = None
        audit(db, actor, "D10", binding.id, "labclear." + reservation.operation + "." + outcome,
              {"attempt_id": attempt.id, "exchange_id": exchange.id})
        db.commit()
    except HTTPException as exc:
        db.rollback()
        db.close()
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        _quarantine(reservation, detail.get("code", "CONNECTOR_CONTEXT_DENIED"))
        raise
    if outcome == "rejected":
        failure(code, 502 if code == "LABCLEAR_REQUEST_REJECTED" else 503)
    return response


@router.post("/import")
def import_lab(body: ImportInput, actor=Depends(current_actor), db=Depends(get_db, scope="function"),
               key: str = Header(alias="Idempotency-Key"), client=Depends(resolve_client)):
    source, task, encounter, snapshot = _authorize_source(db, actor, body.patient_id, body.encounter_id,
        body.task_id, body.source_id, write=True, version=body.source_version)
    values = lab_values(snapshot)
    _lock(db, "his-connector-source:" + digest([actor.user_id, actor.session_id, task.id, source.id, source.version]))
    binding = db.scalar(select(ConnectorBinding).where(ConnectorBinding.actor_id == actor.user_id,
        ConnectorBinding.session_id == actor.session_id, ConnectorBinding.connector == "labclear",
        ConnectorBinding.task_id == task.id, ConnectorBinding.source_id == source.id,
        ConnectorBinding.source_version == source.version).with_for_update())
    if not binding:
        binding = ConnectorBinding(id=uid(), connector="labclear", organization_id=actor.organization_id,
            facility_id=actor.facility_id, actor_id=actor.user_id, session_id=actor.session_id, patient_id=body.patient_id,
            encounter_id=body.encounter_id, task_id=task.id, source_id=source.id, source_version=source.version,
            source_hash=digest(snapshot), source_snapshot=snapshot, lab_values=values, state="reserved")
        db.add(binding)
        db.flush()
    elif binding.source_snapshot != snapshot or binding.source_hash != digest(snapshot):
        failure("CONNECTOR_SOURCE_STALE")
    reservation = _reserve_attempt(db, actor, binding, task, encounter, "import", key, body.model_dump())
    return _execute(db, actor, client, reservation)


@router.get("/bindings")
def list_bindings(patient_id: str, encounter_id: str, actor=Depends(current_actor), db=Depends(get_db, scope="function")):
    revalidate_actor(db, actor)
    require_domain(actor, "D10", True)
    scoped_patient(db, actor, patient_id)
    encounter = scoped_encounter(db, actor, encounter_id)
    if encounter.patient_id != patient_id:
        failure("CONNECTOR_ENCOUNTER_PATIENT_MISMATCH", 404)
    items = db.scalars(select(ConnectorBinding).where(ConnectorBinding.connector == "labclear",
        ConnectorBinding.organization_id == actor.organization_id,
        ConnectorBinding.facility_id == actor.facility_id, ConnectorBinding.actor_id == actor.user_id,
        ConnectorBinding.session_id == actor.session_id, ConnectorBinding.patient_id == patient_id,
        ConnectorBinding.encounter_id == encounter_id).order_by(ConnectorBinding.created_at.desc()).limit(100)).all()
    try:
        ConnectorConfig.from_environment("carebalance-labclear")
        available = True
    except ConnectorUnavailable:
        available = False
    return {"connector": "labclear", "available": available, "items": [binding_dto(row) for row in items]}


@router.post("/bindings/{id}/read")
def read_binding(id: str, actor=Depends(current_actor), db=Depends(get_db, scope="function"), client=Depends(resolve_client)):
    binding, task, encounter = _owned_binding(db, actor, id)
    if not binding.external_report_id:
        failure("CONNECTOR_IMPORT_RECONCILIATION_REQUIRED")
    reservation = _reserve_attempt(db, actor, binding, task, encounter, "read", "read:" + uid(), {})
    return _execute(db, actor, client, reservation)


@router.post("/bindings/{id}/recover")
def recover_binding(id: str, actor=Depends(current_actor), db=Depends(get_db, scope="function")):
    """Expose an owned durable command for explicit resumption, never resend it."""
    binding, task, encounter = _owned_binding(db, actor, id, write=True)
    attempt = db.scalar(select(ConnectorAttempt).where(ConnectorAttempt.binding_id == binding.id,
        ConnectorAttempt.actor_id == actor.user_id, ConnectorAttempt.session_id == actor.session_id,
        ConnectorAttempt.operation.in_(["import", "confirm"]),
        ConnectorAttempt.status.in_(["running", "unknown"]))
        .order_by(ConnectorAttempt.created_at.desc(), ConnectorAttempt.id.desc()).limit(1))
    if attempt is None:
        return {"binding": binding_dto(binding), "pending": None, "retry_allowed": False}
    if attempt.authorization_hash != authorization_hash(actor):
        failure("CONNECTOR_CONTEXT_CHANGED")
    schema = ImportInput if attempt.operation == "import" else ConfirmInput
    # Never return arbitrary persisted JSON as a browser command. Its path and
    # method are server-owned; the body must still satisfy the frozen DTO.
    body = schema.model_validate(attempt.payload).model_dump()
    path = "integrations/labclear/import" if attempt.operation == "import" else (
        "integrations/labclear/bindings/" + binding.id + "/confirm")
    retry_allowed = attempt.status == "unknown" or attempt.lease_expires_at <= utcnow()
    return {"binding": binding_dto(binding), "pending": {"attempt_id": attempt.id,
        "kind": attempt.operation, "path": path, "method": "POST", "key": attempt.operation_key,
        "body": body, "lease_expires_at": attempt.lease_expires_at.isoformat()},
        "retry_allowed": retry_allowed}


@router.post("/bindings/{id}/confirm")
def confirm_binding(id: str, body: ConfirmInput, actor=Depends(current_actor), db=Depends(get_db, scope="function"),
                    key: str = Header(alias="Idempotency-Key"), client=Depends(resolve_client)):
    binding, task, encounter = _owned_binding(db, actor, id, write=True)
    if not binding.external_report_id:
        failure("CONNECTOR_IMPORT_RECONCILIATION_REQUIRED")
    if body.source_version != binding.source_version or body.source_sha256 != binding.source_hash:
        failure("CONNECTOR_SOURCE_STALE")
    if not body.same_person_confirmed:
        failure("SAME_PERSON_CONFIRMATION_REQUIRED", 422)
    if [row.source_index for row in body.fields] != list(range(len(binding.lab_values))):
        failure("CONNECTOR_ROW_MAPPING_REQUIRED", 422)
    reservation = _reserve_attempt(db, actor, binding, task, encounter, "confirm", key, body.model_dump())
    return _execute(db, actor, client, reservation)
