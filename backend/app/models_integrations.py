"""Durable connector scope, immutable source snapshots and transport receipts."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .models import ID, Stamp


class ConnectorBinding(ID, Stamp, Base):
    __tablename__ = "connector_bindings"
    connector: Mapped[str] = mapped_column(String(24), default="labclear")
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("clinical_labs.id"))
    source_version: Mapped[int] = mapped_column(Integer)
    source_hash: Mapped[str] = mapped_column(String(64))
    source_snapshot: Mapped[dict] = mapped_column(JSONB)
    lab_values: Mapped[list] = mapped_column(JSONB)
    external_report_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str] = mapped_column(String(24), default="reserved")
    __table_args__ = (
        UniqueConstraint("actor_id", "session_id", "connector", "task_id", "source_id", "source_version", name="uq_connector_binding_source"),
        ForeignKeyConstraint(["encounter_id", "patient_id", "organization_id", "facility_id"],
                             ["encounters.id", "encounters.patient_id", "encounters.organization_id", "encounters.facility_id"], name="fk_connector_binding_encounter_scope"),
        CheckConstraint("source_version > 0", name="positive_source_version"),
        CheckConstraint("connector = 'labclear'", name="known_connector"),
        CheckConstraint("state IN ('reserved','draft','confirmed','unknown','quarantined')", name="binding_state"),
    )


class ConnectorAttempt(ID, Stamp, Base):
    __tablename__ = "connector_attempts"
    binding_id: Mapped[str] = mapped_column(ForeignKey("connector_bindings.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    operation: Mapped[str] = mapped_column(String(24))
    operation_key: Mapped[str] = mapped_column(String(120))
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    authorization_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default="running")
    lease_id: Mapped[str] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("actor_id", "session_id", "operation_key", name="uq_connector_attempt_actor_session_key"),
        CheckConstraint("operation IN ('import','read','confirm')", name="attempt_operation"),
        CheckConstraint("status IN ('running','succeeded','unknown','rejected','quarantined')", name="attempt_status"),
    )


class ConnectorExchange(ID, Stamp, Base):
    __tablename__ = "connector_exchanges"
    attempt_id: Mapped[str] = mapped_column(ForeignKey("connector_attempts.id"), index=True)
    context_snapshot: Mapped[dict] = mapped_column(JSONB)
    outcome: Mapped[str] = mapped_column(String(24), default="running")
    receipt: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    quarantine_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (CheckConstraint("outcome IN ('running','succeeded','unknown','rejected')", name="exchange_outcome"),)
