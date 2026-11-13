"""Relational clinical workflows; JSON is used only for immutable event snapshots."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Integer, Numeric, DateTime, Boolean, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)
class ClinicalMixin:
    id: Mapped[str] = mapped_column(String(64),primary_key=True,default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey('facilities.id'),index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey('patients.id'),index=True)
    encounter_id: Mapped[str|None] = mapped_column(ForeignKey('encounters.id'),nullable=True,index=True)
    status: Mapped[str] = mapped_column(String(40),index=True)
    version: Mapped[int] = mapped_column(Integer,default=1)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class ServiceSlot(Base):
    __tablename__='clinical_slots'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id: Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    label: Mapped[str]=mapped_column(String(200))
    starts_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    capacity: Mapped[int]=mapped_column(Integer)
    __table_args__=(CheckConstraint('capacity > 0',name='positive_capacity'),)
class Appointment(ClinicalMixin,Base):
    __tablename__='clinical_appointments'
    slot_id: Mapped[str]=mapped_column(ForeignKey('clinical_slots.id'))
    reason: Mapped[str]=mapped_column(Text)
    ticket_number: Mapped[str|None]=mapped_column(String(80),unique=True)
class EmergencyEpisode(ClinicalMixin,Base):
    __tablename__='clinical_emergency'
    presenting_complaint: Mapped[str]=mapped_column(Text)
    triage_level: Mapped[str|None]=mapped_column(String(40))
    assessment: Mapped[str|None]=mapped_column(Text)
    disposition_reason: Mapped[str|None]=mapped_column(Text)
    admission_id: Mapped[str|None]=mapped_column(ForeignKey('clinical_admissions.id'))
class Bed(Base):
    __tablename__='clinical_beds'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    facility_id: Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    ward: Mapped[str]=mapped_column(String(100))
    label: Mapped[str]=mapped_column(String(100))
    active: Mapped[bool]=mapped_column(Boolean,default=True)
class Admission(ClinicalMixin,Base):
    __tablename__='clinical_admissions'
    admission_reason: Mapped[str]=mapped_column(Text)
    current_bed_id: Mapped[str|None]=mapped_column(ForeignKey('clinical_beds.id'))
    discharge_summary: Mapped[str|None]=mapped_column(Text)
class BedAssignment(Base):
    __tablename__='clinical_bed_assignments'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    admission_id: Mapped[str]=mapped_column(ForeignKey('clinical_admissions.id'))
    bed_id: Mapped[str]=mapped_column(ForeignKey('clinical_beds.id'))
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    ended_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    __table_args__=(Index('uq_active_bed','bed_id',unique=True,postgresql_where=text('ended_at IS NULL')),Index('uq_active_admission','admission_id',unique=True,postgresql_where=text('ended_at IS NULL')))
class Handover(ClinicalMixin,Base):
    __tablename__='clinical_handovers'
    summary: Mapped[str]=mapped_column(Text)
    pending_tasks: Mapped[str]=mapped_column(Text)
    receiving_staff_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    signed_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    acknowledged_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
class MedicationOrder(ClinicalMixin,Base):
    __tablename__='clinical_medications'
    order_id: Mapped[str]=mapped_column(ForeignKey('clinical_orders.id'))
    order_version: Mapped[int]=mapped_column(Integer)
    item_id: Mapped[str]=mapped_column(ForeignKey('inventory_items.id'))
    medication_name: Mapped[str]=mapped_column(String(200))
    prescribed_dose: Mapped[str]=mapped_column(String(150))
    route: Mapped[str]=mapped_column(String(80))
    quantity: Mapped[float]=mapped_column(Numeric(18,3))
    unit: Mapped[str]=mapped_column(String(40))
    lot_id: Mapped[str|None]=mapped_column(ForeignKey('inventory_lots.id'))
    location_id: Mapped[str|None]=mapped_column(ForeignKey('stock_locations.id'))
    dispense_movement_id: Mapped[str|None]=mapped_column(ForeignKey('stock_movements.id'))
    dispensed_quantity: Mapped[float]=mapped_column(Numeric(18,3),default=0)
    returned_quantity: Mapped[float]=mapped_column(Numeric(18,3),default=0)
    __table_args__=(CheckConstraint('quantity > 0',name='positive_quantity'),CheckConstraint('returned_quantity >= 0 AND returned_quantity <= dispensed_quantity',name='bounded_return'),)
class MedicationReturn(Base):
    __tablename__='clinical_medication_returns'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    medication_id: Mapped[str]=mapped_column(ForeignKey('clinical_medications.id'))
    quantity: Mapped[float]=mapped_column(Numeric(18,3))
    reason: Mapped[str]=mapped_column(Text)
    disposition: Mapped[str]=mapped_column(String(30),default='quarantine')
    reviewer_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Administration(ClinicalMixin,Base):
    __tablename__='clinical_administrations'
    medication_id: Mapped[str]=mapped_column(ForeignKey('clinical_medications.id'))
    scheduled_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    dose: Mapped[str]=mapped_column(String(150))
    route: Mapped[str]=mapped_column(String(80))
    actual_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    reason: Mapped[str|None]=mapped_column(Text)
    __table_args__=(UniqueConstraint('medication_id','scheduled_at',name='uq_medication_scheduled'),)
class LabRequest(ClinicalMixin,Base):
    __tablename__='clinical_labs'
    order_id: Mapped[str]=mapped_column(ForeignKey('clinical_orders.id'))
    order_version: Mapped[int]=mapped_column(Integer)
    analyte: Mapped[str]=mapped_column(String(150))
    specimen_type: Mapped[str]=mapped_column(String(80))
    accession: Mapped[str|None]=mapped_column(String(80),unique=True)
    result_value: Mapped[str|None]=mapped_column(String(200))
    unit: Mapped[str|None]=mapped_column(String(60))
    reference_range: Mapped[str|None]=mapped_column(String(150))
    critical: Mapped[bool]=mapped_column(Boolean,default=False)
    acknowledged_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    released_to_portal: Mapped[bool]=mapped_column(Boolean,default=False)
class ImagingStudy(ClinicalMixin,Base):
    __tablename__='clinical_imaging'
    asset_id: Mapped[str|None]=mapped_column(ForeignKey('equipment_assets.id'))
    order_id: Mapped[str]=mapped_column(ForeignKey('clinical_orders.id'))
    order_version: Mapped[int]=mapped_column(Integer)
    modality: Mapped[str]=mapped_column(String(40))
    body_site: Mapped[str]=mapped_column(String(120))
    report: Mapped[str|None]=mapped_column(Text)
    file_sha256: Mapped[str|None]=mapped_column(String(64))
    file_path: Mapped[str|None]=mapped_column(String(200))
    file_mime: Mapped[str|None]=mapped_column(String(80))
    released_to_portal: Mapped[bool]=mapped_column(Boolean,default=False)
class ProcedureCase(ClinicalMixin,Base):
    __tablename__='clinical_procedures'
    asset_id: Mapped[str|None]=mapped_column(ForeignKey('equipment_assets.id'))
    cssd_cycle_id: Mapped[str|None]=mapped_column(ForeignKey('cssd_cycles.id'))
    procedure_name: Mapped[str]=mapped_column(String(200))
    room: Mapped[str|None]=mapped_column(String(80))
    starts_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    checklist: Mapped[str|None]=mapped_column(Text)
    checklist_verified_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    anesthesia_record: Mapped[str|None]=mapped_column(Text)
class ICURound(ClinicalMixin,Base):
    __tablename__='clinical_icu_rounds'
    asset_id: Mapped[str|None]=mapped_column(ForeignKey('equipment_assets.id'))
    admission_id: Mapped[str]=mapped_column(ForeignKey('clinical_admissions.id'))
    observation_name: Mapped[str]=mapped_column(String(100))
    observation_value: Mapped[str]=mapped_column(String(120))
    unit: Mapped[str]=mapped_column(String(40))
    observed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    round_note: Mapped[str]=mapped_column(Text)
class PregnancyEpisode(ClinicalMixin,Base):
    __tablename__='clinical_pregnancies'
    gestation_note: Mapped[str]=mapped_column(Text)
    delivery_note: Mapped[str|None]=mapped_column(Text)
    child_patient_id: Mapped[str|None]=mapped_column(ForeignKey('patients.id'),unique=True)
    child_identifier: Mapped[str|None]=mapped_column(String(100))
class PediatricVisit(ClinicalMixin,Base):
    __tablename__='clinical_pediatrics'
    measurement_name: Mapped[str]=mapped_column(String(80))
    measurement_value: Mapped[float]=mapped_column(Numeric(18,3))
    unit: Mapped[str]=mapped_column(String(40))
    measured_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    immunization_note: Mapped[str]=mapped_column(Text,default='')
class RehabPlan(ClinicalMixin,Base):
    __tablename__='clinical_rehab'
    order_id: Mapped[str]=mapped_column(ForeignKey('clinical_orders.id'))
    order_version: Mapped[int]=mapped_column(Integer)
    goals: Mapped[str]=mapped_column(Text)
    assessment: Mapped[str|None]=mapped_column(Text)
    therapist_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
class TherapySession(Base):
    __tablename__='clinical_therapy_sessions'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    plan_id: Mapped[str]=mapped_column(ForeignKey('clinical_rehab.id'))
    appointment_id: Mapped[str]=mapped_column(ForeignKey('clinical_appointments.id'),unique=True)
    scheduled_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    author_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
class TherapyProgress(Base):
    __tablename__='clinical_therapy_progress'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    session_id: Mapped[str]=mapped_column(ForeignKey('clinical_therapy_sessions.id'),unique=True)
    performed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    progress: Mapped[str]=mapped_column(Text)
    author_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
class ImmunizationRecord(Base):
    __tablename__='clinical_immunizations'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    visit_id: Mapped[str]=mapped_column(ForeignKey('clinical_pediatrics.id'))
    item_id: Mapped[str]=mapped_column(ForeignKey('inventory_items.id'))
    lot_id: Mapped[str]=mapped_column(ForeignKey('inventory_lots.id'))
    quantity: Mapped[float]=mapped_column(Numeric(18,3))
    unit: Mapped[str]=mapped_column(String(40))
    administered_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
    __table_args__=(CheckConstraint('quantity > 0',name='positive_quantity'),)
class DentalProcedure(ClinicalMixin,Base):
    __tablename__='clinical_dental'
    tooth_code: Mapped[str]=mapped_column(String(12))
    finding: Mapped[str]=mapped_column(Text)
    procedure_name: Mapped[str]=mapped_column(String(200))
class BloodUnit(Base):
    __tablename__='clinical_blood_units'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    facility_id: Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    identifier: Mapped[str]=mapped_column(String(100),unique=True)
    expiry_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    eligibility_status: Mapped[str]=mapped_column(String(40),default='available')
    version: Mapped[int]=mapped_column(Integer,default=1)
class BloodRequest(ClinicalMixin,Base):
    __tablename__='clinical_blood_requests'
    indication: Mapped[str]=mapped_column(Text)
    unit_id: Mapped[str|None]=mapped_column(ForeignKey('clinical_blood_units.id'))
    verification_evidence: Mapped[str|None]=mapped_column(Text)
    verification_patient_version: Mapped[int|None]=mapped_column(Integer)
    verification_evidence_hash: Mapped[str|None]=mapped_column(String(64))
    verification_unit_version: Mapped[int|None]=mapped_column(Integer)
    verification_request_version: Mapped[int|None]=mapped_column(Integer)
    verified_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    administration_note: Mapped[str|None]=mapped_column(Text)
    __table_args__=(Index('uq_reserved_blood_unit','unit_id',unique=True,postgresql_where=text("status IN ('reserved','compatibility_verified','released','administration_recorded')")),)
class DietOrder(ClinicalMixin,Base):
    __tablename__='clinical_diets'
    diet_description: Mapped[str]=mapped_column(Text)
    allergy_note: Mapped[str]=mapped_column(Text)
    meal_period: Mapped[str]=mapped_column(String(100))
    __table_args__=(UniqueConstraint('encounter_id','meal_period',name='uq_encounter_meal'),)
class Referral(ClinicalMixin,Base):
    __tablename__='clinical_referrals'
    destination: Mapped[str]=mapped_column(String(200))
    reason: Mapped[str]=mapped_column(Text)
    document_revision_id: Mapped[str|None]=mapped_column(ForeignKey('document_versions.id'))
    packet: Mapped[str|None]=mapped_column(Text)
    response_source: Mapped[str|None]=mapped_column(String(200))
    response_note: Mapped[str|None]=mapped_column(Text)
class PortalRequest(ClinicalMixin,Base):
    __tablename__='clinical_portal_requests'
    request_kind: Mapped[str]=mapped_column(String(20))
    document_revision_id: Mapped[str|None]=mapped_column(ForeignKey('document_versions.id'))
    staff_task_id: Mapped[str|None]=mapped_column(ForeignKey('tasks.id'))
    response_note: Mapped[str|None]=mapped_column(Text)
    slot_id: Mapped[str|None]=mapped_column(ForeignKey('clinical_slots.id'))
    reason: Mapped[str]=mapped_column(Text)
    appointment_id: Mapped[str|None]=mapped_column(ForeignKey('clinical_appointments.id'))
class ClinicalEvent(Base):
    __tablename__='clinical_events'
    id: Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    domain: Mapped[str]=mapped_column(String(3),index=True)
    record_id: Mapped[str]=mapped_column(String(64),index=True)
    version: Mapped[int]=mapped_column(Integer)
    action: Mapped[str]=mapped_column(String(50))
    actor_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    snapshot: Mapped[dict]=mapped_column(JSONB)
    reason: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class HandoverTask(Base):
    __tablename__='clinical_handover_tasks'
    handover_id: Mapped[str]=mapped_column(ForeignKey('clinical_handovers.id'),primary_key=True)
    task_id: Mapped[str]=mapped_column(ForeignKey('tasks.id'),primary_key=True)
    task_version: Mapped[int]=mapped_column(Integer)

# Database-level patient/encounter scope integrity supplements API authorization.
from sqlalchemy import ForeignKeyConstraint
for _cls in (Appointment,EmergencyEpisode,Admission,Handover,MedicationOrder,Administration,LabRequest,ImagingStudy,ProcedureCase,ICURound,PregnancyEpisode,PediatricVisit,RehabPlan,DentalProcedure,BloodRequest,DietOrder,Referral,PortalRequest):
    _t=_cls.__table__
    _t.append_constraint(ForeignKeyConstraint(['patient_id','organization_id','facility_id'],['patients.id','patients.organization_id','patients.facility_id'],name='fk_'+_t.name+'_patient_scope'))
    _t.append_constraint(ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'],['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id'],name='fk_'+_t.name+'_encounter_scope'))
    _t.append_constraint(CheckConstraint('version > 0',name='positive_version'))

class DeviceAssignment(ClinicalMixin,Base):
    __tablename__='clinical_device_assignments'
    round_id: Mapped[str]=mapped_column(ForeignKey('clinical_icu_rounds.id'))
    admission_id: Mapped[str]=mapped_column(ForeignKey('clinical_admissions.id'))
    asset_id: Mapped[str]=mapped_column(ForeignKey('equipment_assets.id'))
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    ended_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    released_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    release_reason: Mapped[str|None]=mapped_column(Text)
    __table_args__=(Index('uq_clinical_active_device','asset_id',unique=True,postgresql_where=text('ended_at IS NULL')),ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'],['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id'],name='fk_clinical_device_assignment_encounter_scope'),CheckConstraint('version > 0',name='positive_version'))
