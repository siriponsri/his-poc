"""Dedicated DR source, consent, credential and immutable transport evidence."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .models import ID, Stamp


class ClinicalScope:
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'))
    facility_id: Mapped[str] = mapped_column(ForeignKey('facilities.id'))
    patient_id: Mapped[str] = mapped_column(ForeignKey('patients.id'))
    encounter_id: Mapped[str] = mapped_column(ForeignKey('encounters.id'))


def encounter_fk(name):
    return ForeignKeyConstraint(['encounter_id', 'patient_id', 'organization_id', 'facility_id'],
        ['encounters.id', 'encounters.patient_id', 'encounters.organization_id', 'encounters.facility_id'], name=name)


class DRSourceProvenance(ClinicalScope, ID, Stamp, Base):
    __tablename__ = 'dr_source_provenance'
    source_id: Mapped[str] = mapped_column(ForeignKey('clinical_imaging.id'))
    source_version: Mapped[int] = mapped_column(Integer)
    image_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
    source_origin: Mapped[str] = mapped_column(String(24), default='SYNTHETIC')
    laterality: Mapped[str] = mapped_column(String(1))
    modality: Mapped[str] = mapped_column(String(8))
    capture_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_reference: Mapped[str] = mapped_column(String(240))
    dataset_provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    registrar_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    __table_args__ = (encounter_fk('fk_dr_provenance_encounter_scope'),
        UniqueConstraint('source_id', 'source_version', name='uq_dr_provenance_source_revision'),
        CheckConstraint("(source_origin='SYNTHETIC' AND dataset_provenance IS NULL) OR (source_origin='PUBLIC' AND dataset_provenance IS NOT NULL AND jsonb_typeof(dataset_provenance)='object')", name='registered_source_origin'),
        CheckConstraint("laterality IN ('L','R') AND modality IN ('CFP','UWF')", name='explicit_eye_modality'),
        CheckConstraint('source_version > 0 AND byte_size BETWEEN 1 AND 1048576', name='source_size_revision'))


class DRSourceSet(ClinicalScope, ID, Stamp, Base):
    __tablename__ = 'dr_source_sets'
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'))
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    operation_key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[list] = mapped_column(JSONB)
    consent_snapshot: Mapped[dict] = mapped_column(JSONB)
    destination_id: Mapped[str] = mapped_column(String(64))
    __table_args__ = (encounter_fk('fk_dr_set_encounter_scope'),
        UniqueConstraint('actor_id', 'session_id', 'operation_key', name='uq_dr_set_actor_session_key'),
        CheckConstraint('revision > 0', name='positive_revision'))


class DRSourceSetItem(ID, Base):
    __tablename__ = 'dr_source_set_items'
    source_set_id: Mapped[str] = mapped_column(ForeignKey('dr_source_sets.id'))
    position: Mapped[int] = mapped_column(Integer)
    source_id: Mapped[str] = mapped_column(ForeignKey('clinical_imaging.id'))
    source_version: Mapped[int] = mapped_column(Integer)
    provenance_id: Mapped[str] = mapped_column(ForeignKey('dr_source_provenance.id'))
    source_snapshot: Mapped[dict] = mapped_column(JSONB)
    source_sha256: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint('source_set_id', 'position', name='uq_dr_item_position'),
        UniqueConstraint('source_set_id', 'source_id', name='uq_dr_item_source'),
        CheckConstraint('position BETWEEN 0 AND 7 AND source_version > 0', name='bounded_position_revision'))


class DRCapabilityGrant(ID, Stamp, Base):
    __tablename__ = 'dr_capability_grants'
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'))
    facility_id: Mapped[str] = mapped_column(ForeignKey('facilities.id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    capability: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default='active')
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(16))
    evidence_reference: Mapped[str] = mapped_column(String(240))
    verifier_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (ForeignKeyConstraint(['facility_id', 'organization_id'], ['facilities.id', 'facilities.organization_id'], name='fk_dr_grant_facility_scope'),
        CheckConstraint("capability IN ('dr.grade.confirm','dr.report.sign')", name='explicit_clinical_capability'),
        CheckConstraint("status IN ('active','revoked') AND verification_status='verified'", name='verified_grant_state'),
        CheckConstraint('valid_until > valid_from AND version > 0', name='valid_grant_interval'))


class DRBinding(ClinicalScope, ID, Stamp, Base):
    __tablename__ = 'dr_bindings'
    source_set_id: Mapped[str] = mapped_column(ForeignKey('dr_source_sets.id'))
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    destination_id: Mapped[str] = mapped_column(String(64))
    destination_sha256: Mapped[str] = mapped_column(String(64))
    workspace_id: Mapped[str] = mapped_column(String(64))
    consent_snapshot: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(24), default='reserved')
    __table_args__ = (encounter_fk('fk_dr_binding_encounter_scope'),
        UniqueConstraint('source_set_id', 'actor_id', 'session_id', name='uq_dr_binding_set_actor_session'),
        CheckConstraint("state IN ('reserved','imported','unknown','quarantined')", name='binding_state'))


class DRCapabilityGrantEvent(ID, Stamp, Base):
    __tablename__='dr_capability_grant_events'
    grant_id: Mapped[str]=mapped_column(ForeignKey('dr_capability_grants.id'),index=True)
    organization_id: Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    facility_id: Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    grant_version: Mapped[int]=mapped_column(Integer)
    operation: Mapped[str]=mapped_column(String(16))
    old_snapshot: Mapped[dict | None]=mapped_column(JSONB,nullable=True)
    new_snapshot: Mapped[dict]=mapped_column(JSONB)
    database_principal: Mapped[str]=mapped_column(String(128))
    __table_args__=(UniqueConstraint('grant_id','grant_version',name='uq_dr_grant_event_version'),
        CheckConstraint("operation IN ('INSERT','UPDATE') AND grant_version > 0",name='grant_event_operation'))


class DRAttempt(ID, Stamp, Base):
    __tablename__ = 'dr_attempts'
    binding_id: Mapped[str] = mapped_column(ForeignKey('dr_bindings.id'), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    operation: Mapped[str] = mapped_column(String(24))
    operation_key: Mapped[str] = mapped_column(String(120))
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    authorization_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default='running')
    lease_id: Mapped[str] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint('actor_id', 'session_id', 'operation_key', name='uq_dr_attempt_actor_session_key'),
        CheckConstraint("operation IN ('import','dispatch','read_report')", name='attempt_operation'),
        CheckConstraint("status IN ('running','succeeded','unknown','rejected','quarantined')", name='attempt_status'))


class DRExchange(ID, Stamp, Base):
    __tablename__ = 'dr_exchanges'
    attempt_id: Mapped[str] = mapped_column(ForeignKey('dr_attempts.id'), index=True)
    context_snapshot: Mapped[dict] = mapped_column(JSONB)
    outcome: Mapped[str] = mapped_column(String(24), default='running')
    receipt: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    quarantine_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (CheckConstraint("outcome IN ('running','succeeded','unknown','rejected')", name='exchange_outcome'),)


class DRReportReceipt(ID, Stamp, Base):
    __tablename__ = 'dr_report_receipts'
    binding_id: Mapped[str] = mapped_column(ForeignKey('dr_bindings.id'))
    attempt_id: Mapped[str] = mapped_column(ForeignKey('dr_attempts.id'), unique=True)
    source_set_id: Mapped[str] = mapped_column(ForeignKey('dr_source_sets.id'))
    case_id: Mapped[str] = mapped_column(String(64))
    case_revision: Mapped[int] = mapped_column(Integer)
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    receipt: Mapped[dict] = mapped_column(JSONB)
