"""Durable assistant preparation, human decisions and immutable effect receipts."""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .models import ID, Stamp


class AssistantRun(ID, Stamp, Base):
    __tablename__ = 'assistant_runs'
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey('facilities.id'), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey('patients.id'), index=True)
    encounter_id: Mapped[str] = mapped_column(ForeignKey('encounters.id'), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    profile: Mapped[str] = mapped_column(String(40))
    locale: Mapped[str] = mapped_column(String(8))
    authorization_hash: Mapped[str] = mapped_column(String(64))
    operation_key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    source_digest: Mapped[str] = mapped_column(String(64))
    source_manifest: Mapped[dict] = mapped_column(JSONB)
    inference_view: Mapped[dict] = mapped_column(JSONB)
    input_hash: Mapped[str] = mapped_column(String(64))
    execution_state: Mapped[str] = mapped_column(String(32), default='queued', index=True)
    review_state: Mapped[str] = mapped_column(String(24), default='unavailable')
    provider: Mapped[dict] = mapped_column(JSONB, default=dict)
    usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    measured_cost: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'], ['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id']),
        UniqueConstraint('actor_id','operation_key', name='uq_assistant_run_actor_key'),
        CheckConstraint("profile IN ('visit_preparation','nursing_handover','records_readiness','laboratory_handoff')", name='known_profile'),
        CheckConstraint("execution_state IN ('queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted')", name='execution_state'),
        CheckConstraint("review_state IN ('unavailable','pending','accepted','rejected','superseded','stale')", name='review_state'),
    )


class AssistantRevision(ID, Stamp, Base):
    __tablename__ = 'assistant_revisions'
    run_id: Mapped[str] = mapped_column(ForeignKey('assistant_runs.id'), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    source_digest: Mapped[str] = mapped_column(String(64))
    artifact: Mapped[dict] = mapped_column(JSONB)
    origin: Mapped[str] = mapped_column(String(16))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    __table_args__ = (UniqueConstraint('run_id','version',name='uq_assistant_revision_version'), CheckConstraint("version > 0 AND origin IN ('model','human')",name='revision_origin'))


class AssistantDecision(ID, Stamp, Base):
    __tablename__ = 'assistant_decisions'
    run_id: Mapped[str] = mapped_column(ForeignKey('assistant_runs.id'))
    revision_id: Mapped[str] = mapped_column(ForeignKey('assistant_revisions.id'))
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    authorization_hash: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))
    selected_action_ids: Mapped[list] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint('run_id',name='uq_assistant_decision_run'), CheckConstraint("decision IN ('accepted','rejected')",name='explicit_decision'))


class AssistantEffect(ID, Stamp, Base):
    __tablename__ = 'assistant_effects'
    run_id: Mapped[str] = mapped_column(ForeignKey('assistant_runs.id'), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey('assistant_revisions.id'))
    action_id: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(64))
    task_id: Mapped[str | None] = mapped_column(ForeignKey('tasks.id'), nullable=True, index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey('documents.id'), nullable=True, index=True)
    receipt: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint('revision_id','action_id',name='uq_assistant_effect_revision_action'), UniqueConstraint('run_id','action_id',name='uq_assistant_effect_run_action'))


class AssistantWatch(ID, Stamp, Base):
    __tablename__ = 'assistant_watches'
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'))
    facility_id: Mapped[str] = mapped_column(ForeignKey('facilities.id'))
    patient_id: Mapped[str] = mapped_column(ForeignKey('patients.id'))
    encounter_id: Mapped[str] = mapped_column(ForeignKey('encounters.id'))
    profile: Mapped[str] = mapped_column(String(40))
    locale: Mapped[str] = mapped_column(String(8))
    authorization_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default='active', index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_scan_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_source_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_id: Mapped[str | None] = mapped_column(ForeignKey('assistant_runs.id'), nullable=True)
    last_enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_run_count: Mapped[int] = mapped_column(Integer, default=0)
    max_auto_runs: Mapped[int] = mapped_column(Integer, default=3)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'], ['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id']),
        CheckConstraint("status IN ('active','paused','expired','revoked','exhausted') AND auto_run_count BETWEEN 0 AND 3 AND max_auto_runs BETWEEN 1 AND 3", name='bounded_watch'),
    )
