"""Shared relational core; flexible JSON is limited to immutable action/audit payloads."""
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Date, Boolean, Integer, Numeric, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid(): return str(uuid4())
def utcnow(): return datetime.now(__import__('datetime').timezone.utc)
class ID:
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
class Stamp:
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Organization(ID,Base):
    __tablename__='organizations'
    name:Mapped[str]=mapped_column(String(200))
class Facility(ID,Base):
    __tablename__='facilities'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    name:Mapped[str]=mapped_column(String(200))
    __table_args__=(UniqueConstraint('id','organization_id'),)
class Department(ID,Base):
    __tablename__='departments'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    name:Mapped[str]=mapped_column(String(200))
class Location(ID,Base):
    __tablename__='locations'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    name:Mapped[str]=mapped_column(String(200))
    kind:Mapped[str]=mapped_column(String(32),default='ward')
class User(ID,Stamp,Base):
    __tablename__='users'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    username:Mapped[str]=mapped_column(String(100),unique=True)
    display_name:Mapped[str]=mapped_column(String(200))
    password_hash:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(24),default='active')
    version:Mapped[int]=mapped_column(Integer,default=1)
class Membership(ID,Base):
    __tablename__='memberships'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    role:Mapped[str]=mapped_column(ForeignKey('roles.id'))
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    __table_args__=(UniqueConstraint('user_id','facility_id','role'),)
class SessionRecord(ID,Stamp,Base):
    __tablename__='sessions'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    token_hash:Mapped[str]=mapped_column(String(64),unique=True)
    csrf_hash:Mapped[str]=mapped_column(String(64))
    csrf_token:Mapped[str]=mapped_column(String(100))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    revoked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class LoginAttempt(ID,Stamp,Base):
    __tablename__='login_attempts'
    identity_hash:Mapped[str]=mapped_column(String(64),index=True)
    successful:Mapped[bool]=mapped_column(Boolean)
class Patient(ID,Stamp,Base):
    __tablename__='patients'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'),index=True)
    display_name:Mapped[str]=mapped_column(String(200))
    birth_date:Mapped[date|None]=mapped_column(Date,nullable=True)
    sex:Mapped[str]=mapped_column(String(16),default='unknown')
    status:Mapped[str]=mapped_column(String(24),default='draft')
    version:Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(UniqueConstraint('id','organization_id','facility_id'),UniqueConstraint('id','organization_id'),ForeignKeyConstraint(['facility_id','organization_id'],['facilities.id','facilities.organization_id']),CheckConstraint('version > 0',name='positive_version'))
class PatientIdentifier(ID,Base):
    __tablename__='patient_identifiers'
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'))
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    issuer:Mapped[str]=mapped_column(String(80))
    value:Mapped[str]=mapped_column(String(120))
    __table_args__=(UniqueConstraint('organization_id','issuer','value'),ForeignKeyConstraint(['patient_id','organization_id'],['patients.id','patients.organization_id']))
class UserPatientScope(Base):
    __tablename__='user_patient_scopes'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'),primary_key=True)
class Encounter(ID,Stamp,Base):
    __tablename__='encounters'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'),index=True)
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'),index=True)
    department_id:Mapped[str|None]=mapped_column(ForeignKey('departments.id'),nullable=True)
    practitioner_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    kind:Mapped[str]=mapped_column(String(24),default='OPD')
    status:Mapped[str]=mapped_column(String(24),default='waiting')
    version:Mapped[int]=mapped_column(Integer,default=1)
    disposition:Mapped[str|None]=mapped_column(Text,nullable=True)
    published:Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint('id','patient_id','organization_id','facility_id'),ForeignKeyConstraint(['patient_id','organization_id','facility_id'],['patients.id','patients.organization_id','patients.facility_id']),CheckConstraint('version > 0',name='positive_version'))
class Task(ID,Stamp,Base):
    __tablename__='tasks'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'),index=True)
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'),index=True)
    encounter_id:Mapped[str]=mapped_column(ForeignKey('encounters.id'),index=True)
    domain:Mapped[str]=mapped_column(String(8))
    kind:Mapped[str]=mapped_column(String(64))
    title:Mapped[str]=mapped_column(String(240))
    status:Mapped[str]=mapped_column(String(24),default='open')
    version:Mapped[int]=mapped_column(Integer,default=1)
    assignee_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    __table_args__=(ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'],['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id']),)
class Document(ID,Stamp,Base):
    __tablename__='documents'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'),index=True)
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'),index=True)
    encounter_id:Mapped[str]=mapped_column(ForeignKey('encounters.id'),index=True)
    title:Mapped[str]=mapped_column(String(240))
    status:Mapped[str]=mapped_column(String(24),default='draft')
    version:Mapped[int]=mapped_column(Integer,default=1)
    current_version_id:Mapped[str|None]=mapped_column(String(64),nullable=True)
    published:Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'],['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id']),ForeignKeyConstraint(['current_version_id','id'],['document_versions.id','document_versions.document_id'],name='fk_documents_current_owned_revision',use_alter=True,deferrable=True,initially='DEFERRED'))
class DocumentVersion(ID,Stamp,Base):
    __tablename__='document_versions'
    document_id:Mapped[str]=mapped_column(ForeignKey('documents.id'),index=True)
    version:Mapped[int]=mapped_column(Integer)
    content:Mapped[str]=mapped_column(Text)
    content_hash:Mapped[str]=mapped_column(String(64))
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
    reason:Mapped[str|None]=mapped_column(Text,nullable=True)
    __table_args__=(UniqueConstraint('document_id','version'),UniqueConstraint('id','document_id'))
class DocumentAttestation(ID,Stamp,Base):
    __tablename__='document_attestations'
    document_version_id:Mapped[str]=mapped_column(ForeignKey('document_versions.id'))
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    content_hash:Mapped[str]=mapped_column(String(64))
    __table_args__=(UniqueConstraint('document_version_id'),)
class ClinicalOrder(ID,Stamp,Base):
    __tablename__='clinical_orders'
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'))
    encounter_id:Mapped[str]=mapped_column(ForeignKey('encounters.id'),index=True)
    task_id:Mapped[str|None]=mapped_column(ForeignKey('tasks.id'),nullable=True)
    requester_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    kind:Mapped[str]=mapped_column(String(24))
    code:Mapped[str]=mapped_column(String(80))
    label:Mapped[str]=mapped_column(String(240))
    instructions:Mapped[str]=mapped_column(Text,default='')
    quantity:Mapped[Decimal]=mapped_column(Numeric(18,3),default=1)
    unit:Mapped[str]=mapped_column(String(40),default='unit')
    status:Mapped[str]=mapped_column(String(24),default='draft')
    version:Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(ForeignKeyConstraint(['encounter_id','patient_id','organization_id','facility_id'],['encounters.id','encounters.patient_id','encounters.organization_id','encounters.facility_id']),CheckConstraint('quantity > 0',name='positive_quantity'))
class OrderRevision(ID,Stamp,Base):
    __tablename__='order_revisions'
    order_id:Mapped[str]=mapped_column(ForeignKey('clinical_orders.id'))
    version:Mapped[int]=mapped_column(Integer)
    instructions:Mapped[str]=mapped_column(Text)
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    __table_args__=(UniqueConstraint('order_id','version'),)
class InferenceRun(ID,Stamp,Base):
    __tablename__='inference_runs'
    task_id:Mapped[str]=mapped_column(ForeignKey('tasks.id'),index=True)
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    provider:Mapped[str]=mapped_column(String(64),default='mock_demo')
    outcome:Mapped[str]=mapped_column(String(24))
    reason:Mapped[str|None]=mapped_column(Text,nullable=True)
    elapsed_ms:Mapped[int]=mapped_column(Integer)
    measured_cost:Mapped[Decimal|None]=mapped_column(Numeric(18,6),nullable=True)
    usage:Mapped[dict|None]=mapped_column(JSONB,nullable=True)
    operation_key:Mapped[str|None]=mapped_column(String(120),nullable=True)
    request_hash:Mapped[str|None]=mapped_column(String(64),nullable=True)
    authorization_hash:Mapped[str|None]=mapped_column(String(64),nullable=True)
    context_snapshot:Mapped[dict|None]=mapped_column(JSONB,nullable=True)
    provenance:Mapped[dict|None]=mapped_column(JSONB,nullable=True)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    __table_args__=(UniqueConstraint('actor_id','operation_key'),)
class Proposal(ID,Stamp,Base):
    __tablename__='proposals'
    task_id:Mapped[str]=mapped_column(ForeignKey('tasks.id'),index=True)
    run_id:Mapped[str]=mapped_column(ForeignKey('inference_runs.id'))
    document_version_id:Mapped[str]=mapped_column(ForeignKey('document_versions.id'))
    encounter_version:Mapped[int]=mapped_column(Integer)
    task_version:Mapped[int]=mapped_column(Integer)
    version:Mapped[int]=mapped_column(Integer,default=1)
    status:Mapped[str]=mapped_column(String(24),default='pending')
    action_canonical:Mapped[str]=mapped_column(Text)
    action_hash:Mapped[str]=mapped_column(String(64))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class ProposalVersion(ID,Stamp,Base):
    __tablename__='proposal_versions'
    proposal_id:Mapped[str]=mapped_column(ForeignKey('proposals.id'))
    version:Mapped[int]=mapped_column(Integer)
    action_canonical:Mapped[str]=mapped_column(Text)
    action_hash:Mapped[str]=mapped_column(String(64))
    __table_args__=(UniqueConstraint('proposal_id','version'),)
class HumanReview(ID,Stamp,Base):
    __tablename__='human_reviews'
    proposal_id:Mapped[str]=mapped_column(ForeignKey('proposals.id'),index=True)
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    version:Mapped[int]=mapped_column(Integer)
    action_hash:Mapped[str]=mapped_column(String(64))
    decision:Mapped[str]=mapped_column(String(24))
    edited_text:Mapped[str|None]=mapped_column(Text,nullable=True)
class CommittedResult(ID,Stamp,Base):
    __tablename__='committed_results'
    proposal_id:Mapped[str]=mapped_column(ForeignKey('proposals.id'),unique=True)
    task_id:Mapped[str]=mapped_column(ForeignKey('tasks.id'),unique=True)
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    version:Mapped[int]=mapped_column(Integer)
    action_hash:Mapped[str]=mapped_column(String(64))
    action_canonical:Mapped[str]=mapped_column(Text)
    operation_key:Mapped[str]=mapped_column(String(120))
class AuditEvent(ID,Stamp,Base):
    __tablename__='audit_events'
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    domain:Mapped[str]=mapped_column(String(8),index=True)
    entity_id:Mapped[str]=mapped_column(String(64),index=True)
    action:Mapped[str]=mapped_column(String(80))
    details:Mapped[dict]=mapped_column(JSONB,default=dict)
class Operation(Stamp,Base):
    __tablename__='operations'
    authorization_hash:Mapped[str]=mapped_column(String(64))
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'))
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    key:Mapped[str]=mapped_column(String(120),primary_key=True)
    operation:Mapped[str]=mapped_column(String(180))
    payload_hash:Mapped[str]=mapped_column(String(64))
    response:Mapped[dict]=mapped_column(JSONB)

class Role(Base):
    __tablename__='roles'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    label:Mapped[str]=mapped_column(String(120))
class Permission(Base):
    __tablename__='permissions'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
class RolePermission(Base):
    __tablename__='role_permissions'
    role_id:Mapped[str]=mapped_column(ForeignKey('roles.id'),primary_key=True)
    permission_id:Mapped[str]=mapped_column(ForeignKey('permissions.id'),primary_key=True)
class CareAssignment(Base):
    __tablename__='care_assignments'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    patient_id:Mapped[str]=mapped_column(ForeignKey('patients.id'),primary_key=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
class SeedRun(Base):
    __tablename__='seed_runs'
    version:Mapped[str]=mapped_column(String(64),primary_key=True)
    completed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class SecurityEvent(ID,Stamp,Base):
    __tablename__='security_events'
    organization_id:Mapped[str|None]=mapped_column(ForeignKey('organizations.id'),nullable=True)
    facility_id:Mapped[str|None]=mapped_column(ForeignKey('facilities.id'),nullable=True)
    actor_id:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    method:Mapped[str]=mapped_column(String(8))
    route_template:Mapped[str]=mapped_column(String(200))
    status_code:Mapped[int]=mapped_column(Integer)
    event:Mapped[str]=mapped_column(String(64))
