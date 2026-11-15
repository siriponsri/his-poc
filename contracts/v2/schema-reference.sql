-- REFERENCE ONLY: apply Alembic migrations, not this export.

CREATE TABLE assistant_decisions (
	run_id VARCHAR(64) NOT NULL, 
	revision_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	authorization_hash VARCHAR(64) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	decision VARCHAR(16) NOT NULL, 
	selected_action_ids JSONB NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_assistant_decisions PRIMARY KEY (id), 
	CONSTRAINT uq_assistant_decision_run UNIQUE (run_id), 
	CONSTRAINT ck_assistant_decisions_explicit_decision CHECK (decision IN ('accepted','rejected')), 
	CONSTRAINT fk_assistant_decisions_run_id_assistant_runs FOREIGN KEY(run_id) REFERENCES assistant_runs (id), 
	CONSTRAINT fk_assistant_decisions_revision_id_assistant_revisions FOREIGN KEY(revision_id) REFERENCES assistant_revisions (id), 
	CONSTRAINT fk_assistant_decisions_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE assistant_effects (
	run_id VARCHAR(64) NOT NULL, 
	revision_id VARCHAR(64) NOT NULL, 
	action_id VARCHAR(32) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64), 
	document_id VARCHAR(64), 
	receipt JSONB NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_assistant_effects PRIMARY KEY (id), 
	CONSTRAINT uq_assistant_effect_revision_action UNIQUE (revision_id, action_id), 
	CONSTRAINT uq_assistant_effect_run_action UNIQUE (run_id, action_id), 
	CONSTRAINT fk_assistant_effects_run_id_assistant_runs FOREIGN KEY(run_id) REFERENCES assistant_runs (id), 
	CONSTRAINT fk_assistant_effects_revision_id_assistant_revisions FOREIGN KEY(revision_id) REFERENCES assistant_revisions (id), 
	CONSTRAINT fk_assistant_effects_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_assistant_effects_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id)
)

;

CREATE INDEX ix_assistant_effects_document_id ON assistant_effects (document_id);

CREATE INDEX ix_assistant_effects_run_id ON assistant_effects (run_id);

CREATE INDEX ix_assistant_effects_task_id ON assistant_effects (task_id);


CREATE TABLE assistant_revisions (
	run_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	source_digest VARCHAR(64) NOT NULL, 
	artifact JSONB NOT NULL, 
	origin VARCHAR(16) NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_assistant_revisions PRIMARY KEY (id), 
	CONSTRAINT uq_assistant_revision_version UNIQUE (run_id, version), 
	CONSTRAINT ck_assistant_revisions_revision_origin CHECK (version > 0 AND origin IN ('model','human')), 
	CONSTRAINT fk_assistant_revisions_run_id_assistant_runs FOREIGN KEY(run_id) REFERENCES assistant_runs (id), 
	CONSTRAINT fk_assistant_revisions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
)

;

CREATE INDEX ix_assistant_revisions_run_id ON assistant_revisions (run_id);


CREATE TABLE assistant_runs (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	profile VARCHAR(40) NOT NULL, 
	locale VARCHAR(8) NOT NULL, 
	authorization_hash VARCHAR(64) NOT NULL, 
	operation_key VARCHAR(120) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	source_digest VARCHAR(64) NOT NULL, 
	source_manifest JSONB NOT NULL, 
	inference_view JSONB NOT NULL, 
	input_hash VARCHAR(64) NOT NULL, 
	execution_state VARCHAR(32) NOT NULL, 
	review_state VARCHAR(24) NOT NULL, 
	provider JSONB NOT NULL, 
	usage JSONB, 
	measured_cost VARCHAR(80), 
	error VARCHAR(80), 
	lease_id VARCHAR(64), 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	hold_until TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_assistant_runs PRIMARY KEY (id), 
	CONSTRAINT fk_assistant_runs_encounter_id_patient_id_organization__7393 FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT uq_assistant_run_actor_key UNIQUE (actor_id, operation_key), 
	CONSTRAINT ck_assistant_runs_known_profile CHECK (profile IN ('visit_preparation','nursing_handover','records_readiness','laboratory_handoff')), 
	CONSTRAINT ck_assistant_runs_execution_state CHECK (execution_state IN ('queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted')), 
	CONSTRAINT ck_assistant_runs_review_state CHECK (review_state IN ('unavailable','pending','accepted','rejected','superseded','stale')), 
	CONSTRAINT fk_assistant_runs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_assistant_runs_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_assistant_runs_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_assistant_runs_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_assistant_runs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_assistant_runs_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id)
)

;

CREATE INDEX ix_assistant_runs_actor_id ON assistant_runs (actor_id);

CREATE INDEX ix_assistant_runs_encounter_id ON assistant_runs (encounter_id);

CREATE INDEX ix_assistant_runs_execution_state ON assistant_runs (execution_state);

CREATE INDEX ix_assistant_runs_facility_id ON assistant_runs (facility_id);

CREATE INDEX ix_assistant_runs_organization_id ON assistant_runs (organization_id);

CREATE INDEX ix_assistant_runs_patient_id ON assistant_runs (patient_id);


CREATE TABLE assistant_watches (
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	profile VARCHAR(40) NOT NULL, 
	locale VARCHAR(8) NOT NULL, 
	authorization_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	next_scan_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_source_digest VARCHAR(64), 
	last_run_id VARCHAR(64), 
	last_enqueued_at TIMESTAMP WITH TIME ZONE, 
	auto_run_count INTEGER NOT NULL, 
	max_auto_runs INTEGER NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_assistant_watches PRIMARY KEY (id), 
	CONSTRAINT fk_assistant_watches_encounter_id_patient_id_organizati_341f FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_assistant_watches_bounded_watch CHECK (status IN ('active','paused','expired','revoked','exhausted') AND auto_run_count BETWEEN 0 AND 3 AND max_auto_runs BETWEEN 1 AND 3), 
	CONSTRAINT fk_assistant_watches_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_assistant_watches_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), 
	CONSTRAINT fk_assistant_watches_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_assistant_watches_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_assistant_watches_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_assistant_watches_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_assistant_watches_last_run_id_assistant_runs FOREIGN KEY(last_run_id) REFERENCES assistant_runs (id)
)

;

CREATE INDEX ix_assistant_watches_actor_id ON assistant_watches (actor_id);

CREATE INDEX ix_assistant_watches_next_scan_at ON assistant_watches (next_scan_at);

CREATE INDEX ix_assistant_watches_status ON assistant_watches (status);


CREATE TABLE audit_events (
	facility_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	domain VARCHAR(8) NOT NULL, 
	entity_id VARCHAR(64) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	details JSONB NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_audit_events PRIMARY KEY (id), 
	CONSTRAINT fk_audit_events_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_audit_events_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_audit_events_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_audit_events_domain ON audit_events (domain);

CREATE INDEX ix_audit_events_entity_id ON audit_events (entity_id);

CREATE INDEX ix_audit_events_organization_id ON audit_events (organization_id);


CREATE TABLE budget_versions (
	department_id VARCHAR(64) NOT NULL, 
	period VARCHAR(30) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	method_version VARCHAR(100) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_budget_versions PRIMARY KEY (id), 
	CONSTRAINT fk_budget_versions_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
	CONSTRAINT fk_budget_versions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_budget_versions_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_budget_versions_facility_id ON budget_versions (facility_id);

CREATE INDEX ix_budget_versions_organization_id ON budget_versions (organization_id);


CREATE TABLE care_assignments (
	user_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	active BOOLEAN NOT NULL, 
	CONSTRAINT pk_care_assignments PRIMARY KEY (user_id, patient_id), 
	CONSTRAINT fk_care_assignments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_care_assignments_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id)
)

;


CREATE TABLE charges (
	encounter_id VARCHAR(64) NOT NULL, 
	invoice_id VARCHAR(64), 
	price_version_id VARCHAR(64), 
	source_id VARCHAR(200) NOT NULL, 
	label VARCHAR(300) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	unit_price NUMERIC(18, 2) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_charges PRIMARY KEY (id), 
	CONSTRAINT uq_charges_organization_id_source_id UNIQUE (organization_id, source_id), 
	CONSTRAINT ck_charges_erp_check_2 CHECK (quantity > 0 AND unit_price >= 0 AND amount >= 0), 
	CONSTRAINT fk_charges_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_charges_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	CONSTRAINT fk_charges_price_version_id_price_versions FOREIGN KEY(price_version_id) REFERENCES price_versions (id), 
	CONSTRAINT fk_charges_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_charges_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_charges_encounter_id ON charges (encounter_id);

CREATE INDEX ix_charges_facility_id ON charges (facility_id);

CREATE INDEX ix_charges_organization_id ON charges (organization_id);


CREATE TABLE claim_lines (
	claim_id VARCHAR(64) NOT NULL, 
	charge_id VARCHAR(64) NOT NULL, 
	billed NUMERIC(18, 2) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_claim_lines PRIMARY KEY (id), 
	CONSTRAINT uq_claim_lines_claim_id_charge_id UNIQUE (claim_id, charge_id), 
	CONSTRAINT fk_claim_lines_claim_id_claims FOREIGN KEY(claim_id) REFERENCES claims (id), 
	CONSTRAINT fk_claim_lines_charge_id_charges FOREIGN KEY(charge_id) REFERENCES charges (id), 
	CONSTRAINT fk_claim_lines_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_claim_lines_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_claim_lines_claim_id ON claim_lines (claim_id);

CREATE INDEX ix_claim_lines_facility_id ON claim_lines (facility_id);

CREATE INDEX ix_claim_lines_organization_id ON claim_lines (organization_id);


CREATE TABLE claims (
	invoice_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	payer_name VARCHAR(200) NOT NULL, 
	submitted NUMERIC(18, 2) NOT NULL, 
	approved NUMERIC(18, 2) NOT NULL, 
	exported_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_claims PRIMARY KEY (id), 
	CONSTRAINT uq_claims_invoice_id UNIQUE (invoice_id), 
	CONSTRAINT fk_claims_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	CONSTRAINT fk_claims_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_claims_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_claims_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_claims_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_claims_facility_id ON claims (facility_id);

CREATE INDEX ix_claims_organization_id ON claims (organization_id);


CREATE TABLE clinical_administrations (
	medication_id VARCHAR(64) NOT NULL, 
	scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	dose VARCHAR(150) NOT NULL, 
	route VARCHAR(80) NOT NULL, 
	actual_at TIMESTAMP WITH TIME ZONE, 
	reason TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_administrations PRIMARY KEY (id), 
	CONSTRAINT uq_medication_scheduled UNIQUE (medication_id, scheduled_at), 
	CONSTRAINT fk_clinical_administrations_medication_id_clinical_medications FOREIGN KEY(medication_id) REFERENCES clinical_medications (id), 
	CONSTRAINT fk_clinical_administrations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_administrations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_administrations_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_administrations_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_administrations_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_administrations_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_administrations_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_administrations_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_administrations_encounter_id ON clinical_administrations (encounter_id);

CREATE INDEX ix_clinical_administrations_facility_id ON clinical_administrations (facility_id);

CREATE INDEX ix_clinical_administrations_organization_id ON clinical_administrations (organization_id);

CREATE INDEX ix_clinical_administrations_patient_id ON clinical_administrations (patient_id);

CREATE INDEX ix_clinical_administrations_status ON clinical_administrations (status);


CREATE TABLE clinical_admissions (
	admission_reason TEXT NOT NULL, 
	current_bed_id VARCHAR(64), 
	discharge_summary TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_admissions PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_admissions_current_bed_id_clinical_beds FOREIGN KEY(current_bed_id) REFERENCES clinical_beds (id), 
	CONSTRAINT fk_clinical_admissions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_admissions_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_admissions_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_admissions_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_admissions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_admissions_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_admissions_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_admissions_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_admissions_encounter_id ON clinical_admissions (encounter_id);

CREATE INDEX ix_clinical_admissions_facility_id ON clinical_admissions (facility_id);

CREATE INDEX ix_clinical_admissions_organization_id ON clinical_admissions (organization_id);

CREATE INDEX ix_clinical_admissions_patient_id ON clinical_admissions (patient_id);

CREATE INDEX ix_clinical_admissions_status ON clinical_admissions (status);


CREATE TABLE clinical_appointments (
	slot_id VARCHAR(64) NOT NULL, 
	reason TEXT NOT NULL, 
	ticket_number VARCHAR(80), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_appointments PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_appointments_slot_id_clinical_slots FOREIGN KEY(slot_id) REFERENCES clinical_slots (id), 
	CONSTRAINT uq_clinical_appointments_ticket_number UNIQUE (ticket_number), 
	CONSTRAINT fk_clinical_appointments_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_appointments_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_appointments_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_appointments_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_appointments_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_appointments_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_appointments_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_appointments_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_appointments_encounter_id ON clinical_appointments (encounter_id);

CREATE INDEX ix_clinical_appointments_facility_id ON clinical_appointments (facility_id);

CREATE INDEX ix_clinical_appointments_organization_id ON clinical_appointments (organization_id);

CREATE INDEX ix_clinical_appointments_patient_id ON clinical_appointments (patient_id);

CREATE INDEX ix_clinical_appointments_status ON clinical_appointments (status);


CREATE TABLE clinical_bed_assignments (
	id VARCHAR(64) NOT NULL, 
	admission_id VARCHAR(64) NOT NULL, 
	bed_id VARCHAR(64) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_clinical_bed_assignments PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_bed_assignments_admission_id_clinical_admissions FOREIGN KEY(admission_id) REFERENCES clinical_admissions (id), 
	CONSTRAINT fk_clinical_bed_assignments_bed_id_clinical_beds FOREIGN KEY(bed_id) REFERENCES clinical_beds (id)
)

;

CREATE UNIQUE INDEX uq_active_admission ON clinical_bed_assignments (admission_id) WHERE ended_at IS NULL;

CREATE UNIQUE INDEX uq_active_bed ON clinical_bed_assignments (bed_id) WHERE ended_at IS NULL;


CREATE TABLE clinical_beds (
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	ward VARCHAR(100) NOT NULL, 
	label VARCHAR(100) NOT NULL, 
	active BOOLEAN NOT NULL, 
	CONSTRAINT pk_clinical_beds PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_beds_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_beds_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;


CREATE TABLE clinical_blood_requests (
	indication TEXT NOT NULL, 
	unit_id VARCHAR(64), 
	verification_evidence TEXT, 
	verification_patient_version INTEGER, 
	verification_evidence_hash VARCHAR(64), 
	verification_unit_version INTEGER, 
	verification_request_version INTEGER, 
	verified_by VARCHAR(64), 
	administration_note TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_blood_requests PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_blood_requests_unit_id_clinical_blood_units FOREIGN KEY(unit_id) REFERENCES clinical_blood_units (id), 
	CONSTRAINT fk_clinical_blood_requests_verified_by_users FOREIGN KEY(verified_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_blood_requests_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_blood_requests_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_blood_requests_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_blood_requests_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_blood_requests_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_blood_requests_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_blood_requests_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_blood_requests_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_blood_requests_encounter_id ON clinical_blood_requests (encounter_id);

CREATE INDEX ix_clinical_blood_requests_facility_id ON clinical_blood_requests (facility_id);

CREATE INDEX ix_clinical_blood_requests_organization_id ON clinical_blood_requests (organization_id);

CREATE INDEX ix_clinical_blood_requests_patient_id ON clinical_blood_requests (patient_id);

CREATE INDEX ix_clinical_blood_requests_status ON clinical_blood_requests (status);

CREATE UNIQUE INDEX uq_reserved_blood_unit ON clinical_blood_requests (unit_id) WHERE status IN ('reserved','compatibility_verified','released','administration_recorded');


CREATE TABLE clinical_blood_units (
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	identifier VARCHAR(100) NOT NULL, 
	expiry_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	eligibility_status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_clinical_blood_units PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_blood_units_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_blood_units_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT uq_clinical_blood_units_identifier UNIQUE (identifier)
)

;


CREATE TABLE clinical_dental (
	tooth_code VARCHAR(12) NOT NULL, 
	finding TEXT NOT NULL, 
	procedure_name VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_dental PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_dental_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_dental_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_dental_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_dental_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_dental_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_dental_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_dental_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_dental_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_dental_encounter_id ON clinical_dental (encounter_id);

CREATE INDEX ix_clinical_dental_facility_id ON clinical_dental (facility_id);

CREATE INDEX ix_clinical_dental_organization_id ON clinical_dental (organization_id);

CREATE INDEX ix_clinical_dental_patient_id ON clinical_dental (patient_id);

CREATE INDEX ix_clinical_dental_status ON clinical_dental (status);


CREATE TABLE clinical_device_assignments (
	round_id VARCHAR(64) NOT NULL, 
	admission_id VARCHAR(64) NOT NULL, 
	asset_id VARCHAR(64) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	released_by VARCHAR(64), 
	release_reason TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_device_assignments PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_device_assignment_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_device_assignments_positive_version CHECK (version > 0), 
	CONSTRAINT fk_clinical_device_assignments_round_id_clinical_icu_rounds FOREIGN KEY(round_id) REFERENCES clinical_icu_rounds (id), 
	CONSTRAINT fk_clinical_device_assignments_admission_id_clinical_admissions FOREIGN KEY(admission_id) REFERENCES clinical_admissions (id), 
	CONSTRAINT fk_clinical_device_assignments_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_clinical_device_assignments_released_by_users FOREIGN KEY(released_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_device_assignments_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_device_assignments_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_device_assignments_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_device_assignments_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_device_assignments_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
)

;

CREATE INDEX ix_clinical_device_assignments_encounter_id ON clinical_device_assignments (encounter_id);

CREATE INDEX ix_clinical_device_assignments_facility_id ON clinical_device_assignments (facility_id);

CREATE INDEX ix_clinical_device_assignments_organization_id ON clinical_device_assignments (organization_id);

CREATE INDEX ix_clinical_device_assignments_patient_id ON clinical_device_assignments (patient_id);

CREATE INDEX ix_clinical_device_assignments_status ON clinical_device_assignments (status);

CREATE UNIQUE INDEX uq_clinical_active_device ON clinical_device_assignments (asset_id) WHERE ended_at IS NULL;


CREATE TABLE clinical_diets (
	diet_description TEXT NOT NULL, 
	allergy_note TEXT NOT NULL, 
	meal_period VARCHAR(100) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_diets PRIMARY KEY (id), 
	CONSTRAINT uq_encounter_meal UNIQUE (encounter_id, meal_period), 
	CONSTRAINT fk_clinical_diets_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_diets_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_diets_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_diets_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_diets_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_diets_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_diets_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_diets_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_diets_encounter_id ON clinical_diets (encounter_id);

CREATE INDEX ix_clinical_diets_facility_id ON clinical_diets (facility_id);

CREATE INDEX ix_clinical_diets_organization_id ON clinical_diets (organization_id);

CREATE INDEX ix_clinical_diets_patient_id ON clinical_diets (patient_id);

CREATE INDEX ix_clinical_diets_status ON clinical_diets (status);


CREATE TABLE clinical_emergency (
	presenting_complaint TEXT NOT NULL, 
	triage_level VARCHAR(40), 
	assessment TEXT, 
	disposition_reason TEXT, 
	admission_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_emergency PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_emergency_admission_id_clinical_admissions FOREIGN KEY(admission_id) REFERENCES clinical_admissions (id), 
	CONSTRAINT fk_clinical_emergency_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_emergency_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_emergency_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_emergency_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_emergency_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_emergency_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_emergency_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_emergency_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_emergency_encounter_id ON clinical_emergency (encounter_id);

CREATE INDEX ix_clinical_emergency_facility_id ON clinical_emergency (facility_id);

CREATE INDEX ix_clinical_emergency_organization_id ON clinical_emergency (organization_id);

CREATE INDEX ix_clinical_emergency_patient_id ON clinical_emergency (patient_id);

CREATE INDEX ix_clinical_emergency_status ON clinical_emergency (status);


CREATE TABLE clinical_events (
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	domain VARCHAR(3) NOT NULL, 
	record_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	action VARCHAR(50) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	snapshot JSONB NOT NULL, 
	reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_events PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_events_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_events_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_clinical_events_domain ON clinical_events (domain);

CREATE INDEX ix_clinical_events_organization_id ON clinical_events (organization_id);

CREATE INDEX ix_clinical_events_record_id ON clinical_events (record_id);


CREATE TABLE clinical_handover_tasks (
	handover_id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	task_version INTEGER NOT NULL, 
	CONSTRAINT pk_clinical_handover_tasks PRIMARY KEY (handover_id, task_id), 
	CONSTRAINT fk_clinical_handover_tasks_handover_id_clinical_handovers FOREIGN KEY(handover_id) REFERENCES clinical_handovers (id), 
	CONSTRAINT fk_clinical_handover_tasks_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id)
)

;


CREATE TABLE clinical_handovers (
	summary TEXT NOT NULL, 
	pending_tasks TEXT NOT NULL, 
	receiving_staff_id VARCHAR(64) NOT NULL, 
	signed_by VARCHAR(64), 
	acknowledged_by VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_handovers PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_handovers_receiving_staff_id_users FOREIGN KEY(receiving_staff_id) REFERENCES users (id), 
	CONSTRAINT fk_clinical_handovers_signed_by_users FOREIGN KEY(signed_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_handovers_acknowledged_by_users FOREIGN KEY(acknowledged_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_handovers_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_handovers_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_handovers_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_handovers_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_handovers_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_handovers_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_handovers_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_handovers_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_handovers_encounter_id ON clinical_handovers (encounter_id);

CREATE INDEX ix_clinical_handovers_facility_id ON clinical_handovers (facility_id);

CREATE INDEX ix_clinical_handovers_organization_id ON clinical_handovers (organization_id);

CREATE INDEX ix_clinical_handovers_patient_id ON clinical_handovers (patient_id);

CREATE INDEX ix_clinical_handovers_status ON clinical_handovers (status);


CREATE TABLE clinical_icu_rounds (
	asset_id VARCHAR(64), 
	admission_id VARCHAR(64) NOT NULL, 
	observation_name VARCHAR(100) NOT NULL, 
	observation_value VARCHAR(120) NOT NULL, 
	unit VARCHAR(40) NOT NULL, 
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	round_note TEXT NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_icu_rounds PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_icu_rounds_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_clinical_icu_rounds_admission_id_clinical_admissions FOREIGN KEY(admission_id) REFERENCES clinical_admissions (id), 
	CONSTRAINT fk_clinical_icu_rounds_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_icu_rounds_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_icu_rounds_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_icu_rounds_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_icu_rounds_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_icu_rounds_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_icu_rounds_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_icu_rounds_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_icu_rounds_encounter_id ON clinical_icu_rounds (encounter_id);

CREATE INDEX ix_clinical_icu_rounds_facility_id ON clinical_icu_rounds (facility_id);

CREATE INDEX ix_clinical_icu_rounds_organization_id ON clinical_icu_rounds (organization_id);

CREATE INDEX ix_clinical_icu_rounds_patient_id ON clinical_icu_rounds (patient_id);

CREATE INDEX ix_clinical_icu_rounds_status ON clinical_icu_rounds (status);


CREATE TABLE clinical_imaging (
	asset_id VARCHAR(64), 
	order_id VARCHAR(64) NOT NULL, 
	order_version INTEGER NOT NULL, 
	modality VARCHAR(40) NOT NULL, 
	body_site VARCHAR(120) NOT NULL, 
	report TEXT, 
	file_sha256 VARCHAR(64), 
	file_path VARCHAR(200), 
	file_mime VARCHAR(80), 
	released_to_portal BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_imaging PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_imaging_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_clinical_imaging_order_id_clinical_orders FOREIGN KEY(order_id) REFERENCES clinical_orders (id), 
	CONSTRAINT fk_clinical_imaging_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_imaging_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_imaging_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_imaging_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_imaging_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_imaging_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_imaging_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_imaging_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_imaging_encounter_id ON clinical_imaging (encounter_id);

CREATE INDEX ix_clinical_imaging_facility_id ON clinical_imaging (facility_id);

CREATE INDEX ix_clinical_imaging_organization_id ON clinical_imaging (organization_id);

CREATE INDEX ix_clinical_imaging_patient_id ON clinical_imaging (patient_id);

CREATE INDEX ix_clinical_imaging_status ON clinical_imaging (status);


CREATE TABLE clinical_immunizations (
	id VARCHAR(64) NOT NULL, 
	visit_id VARCHAR(64) NOT NULL, 
	item_id VARCHAR(64) NOT NULL, 
	lot_id VARCHAR(64) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	unit VARCHAR(40) NOT NULL, 
	administered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	recorded_by VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_clinical_immunizations PRIMARY KEY (id), 
	CONSTRAINT ck_clinical_immunizations_positive_quantity CHECK (quantity > 0), 
	CONSTRAINT fk_clinical_immunizations_visit_id_clinical_pediatrics FOREIGN KEY(visit_id) REFERENCES clinical_pediatrics (id), 
	CONSTRAINT fk_clinical_immunizations_item_id_inventory_items FOREIGN KEY(item_id) REFERENCES inventory_items (id), 
	CONSTRAINT fk_clinical_immunizations_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT fk_clinical_immunizations_recorded_by_users FOREIGN KEY(recorded_by) REFERENCES users (id)
)

;


CREATE TABLE clinical_labs (
	order_id VARCHAR(64) NOT NULL, 
	order_version INTEGER NOT NULL, 
	analyte VARCHAR(150) NOT NULL, 
	specimen_type VARCHAR(80) NOT NULL, 
	accession VARCHAR(80), 
	result_value VARCHAR(200), 
	unit VARCHAR(60), 
	reference_range VARCHAR(150), 
	critical BOOLEAN NOT NULL, 
	acknowledged_by VARCHAR(64), 
	released_to_portal BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_labs PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_labs_order_id_clinical_orders FOREIGN KEY(order_id) REFERENCES clinical_orders (id), 
	CONSTRAINT uq_clinical_labs_accession UNIQUE (accession), 
	CONSTRAINT fk_clinical_labs_acknowledged_by_users FOREIGN KEY(acknowledged_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_labs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_labs_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_labs_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_labs_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_labs_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_labs_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_labs_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_labs_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_labs_encounter_id ON clinical_labs (encounter_id);

CREATE INDEX ix_clinical_labs_facility_id ON clinical_labs (facility_id);

CREATE INDEX ix_clinical_labs_organization_id ON clinical_labs (organization_id);

CREATE INDEX ix_clinical_labs_patient_id ON clinical_labs (patient_id);

CREATE INDEX ix_clinical_labs_status ON clinical_labs (status);


CREATE TABLE clinical_medication_returns (
	id VARCHAR(64) NOT NULL, 
	medication_id VARCHAR(64) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	reason TEXT NOT NULL, 
	disposition VARCHAR(30) NOT NULL, 
	reviewer_id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_medication_returns PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_medication_returns_medication_id_clinical_m_36c6 FOREIGN KEY(medication_id) REFERENCES clinical_medications (id), 
	CONSTRAINT fk_clinical_medication_returns_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id)
)

;


CREATE TABLE clinical_medications (
	order_id VARCHAR(64) NOT NULL, 
	order_version INTEGER NOT NULL, 
	item_id VARCHAR(64) NOT NULL, 
	medication_name VARCHAR(200) NOT NULL, 
	prescribed_dose VARCHAR(150) NOT NULL, 
	route VARCHAR(80) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	unit VARCHAR(40) NOT NULL, 
	lot_id VARCHAR(64), 
	location_id VARCHAR(64), 
	dispense_movement_id VARCHAR(64), 
	dispensed_quantity NUMERIC(18, 3) NOT NULL, 
	returned_quantity NUMERIC(18, 3) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_medications PRIMARY KEY (id), 
	CONSTRAINT ck_clinical_medications_positive_quantity CHECK (quantity > 0), 
	CONSTRAINT ck_clinical_medications_bounded_return CHECK (returned_quantity >= 0 AND returned_quantity <= dispensed_quantity), 
	CONSTRAINT fk_clinical_medications_order_id_clinical_orders FOREIGN KEY(order_id) REFERENCES clinical_orders (id), 
	CONSTRAINT fk_clinical_medications_item_id_inventory_items FOREIGN KEY(item_id) REFERENCES inventory_items (id), 
	CONSTRAINT fk_clinical_medications_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT fk_clinical_medications_location_id_stock_locations FOREIGN KEY(location_id) REFERENCES stock_locations (id), 
	CONSTRAINT fk_clinical_medications_dispense_movement_id_stock_movements FOREIGN KEY(dispense_movement_id) REFERENCES stock_movements (id), 
	CONSTRAINT fk_clinical_medications_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_medications_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_medications_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_medications_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_medications_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_medications_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_medications_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_medications_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_medications_encounter_id ON clinical_medications (encounter_id);

CREATE INDEX ix_clinical_medications_facility_id ON clinical_medications (facility_id);

CREATE INDEX ix_clinical_medications_organization_id ON clinical_medications (organization_id);

CREATE INDEX ix_clinical_medications_patient_id ON clinical_medications (patient_id);

CREATE INDEX ix_clinical_medications_status ON clinical_medications (status);


CREATE TABLE clinical_orders (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64), 
	requester_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	label VARCHAR(240) NOT NULL, 
	instructions TEXT NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	unit VARCHAR(40) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	version INTEGER NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_orders PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_orders_encounter_id_patient_id_organization_3b2d FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_orders_positive_quantity CHECK (quantity > 0), 
	CONSTRAINT fk_clinical_orders_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_orders_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_orders_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_orders_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_orders_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_clinical_orders_requester_id_users FOREIGN KEY(requester_id) REFERENCES users (id)
)

;

CREATE INDEX ix_clinical_orders_encounter_id ON clinical_orders (encounter_id);

CREATE INDEX ix_clinical_orders_organization_id ON clinical_orders (organization_id);


CREATE TABLE clinical_pediatrics (
	measurement_name VARCHAR(80) NOT NULL, 
	measurement_value NUMERIC(18, 3) NOT NULL, 
	unit VARCHAR(40) NOT NULL, 
	measured_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	immunization_note TEXT NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_pediatrics PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_pediatrics_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_pediatrics_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_pediatrics_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_pediatrics_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_pediatrics_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_pediatrics_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_pediatrics_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_pediatrics_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_pediatrics_encounter_id ON clinical_pediatrics (encounter_id);

CREATE INDEX ix_clinical_pediatrics_facility_id ON clinical_pediatrics (facility_id);

CREATE INDEX ix_clinical_pediatrics_organization_id ON clinical_pediatrics (organization_id);

CREATE INDEX ix_clinical_pediatrics_patient_id ON clinical_pediatrics (patient_id);

CREATE INDEX ix_clinical_pediatrics_status ON clinical_pediatrics (status);


CREATE TABLE clinical_portal_requests (
	request_kind VARCHAR(20) NOT NULL, 
	document_revision_id VARCHAR(64), 
	staff_task_id VARCHAR(64), 
	response_note TEXT, 
	slot_id VARCHAR(64), 
	reason TEXT NOT NULL, 
	appointment_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_portal_requests PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_portal_requests_document_revision_id_docume_e22f FOREIGN KEY(document_revision_id) REFERENCES document_versions (id), 
	CONSTRAINT fk_clinical_portal_requests_staff_task_id_tasks FOREIGN KEY(staff_task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_clinical_portal_requests_slot_id_clinical_slots FOREIGN KEY(slot_id) REFERENCES clinical_slots (id), 
	CONSTRAINT fk_clinical_portal_requests_appointment_id_clinical_app_86e3 FOREIGN KEY(appointment_id) REFERENCES clinical_appointments (id), 
	CONSTRAINT fk_clinical_portal_requests_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_portal_requests_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_portal_requests_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_portal_requests_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_portal_requests_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_portal_requests_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_portal_requests_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_portal_requests_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_portal_requests_encounter_id ON clinical_portal_requests (encounter_id);

CREATE INDEX ix_clinical_portal_requests_facility_id ON clinical_portal_requests (facility_id);

CREATE INDEX ix_clinical_portal_requests_organization_id ON clinical_portal_requests (organization_id);

CREATE INDEX ix_clinical_portal_requests_patient_id ON clinical_portal_requests (patient_id);

CREATE INDEX ix_clinical_portal_requests_status ON clinical_portal_requests (status);


CREATE TABLE clinical_pregnancies (
	gestation_note TEXT NOT NULL, 
	delivery_note TEXT, 
	child_patient_id VARCHAR(64), 
	child_identifier VARCHAR(100), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_pregnancies PRIMARY KEY (id), 
	CONSTRAINT uq_clinical_pregnancies_child_patient_id UNIQUE (child_patient_id), 
	CONSTRAINT fk_clinical_pregnancies_child_patient_id_patients FOREIGN KEY(child_patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_pregnancies_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_pregnancies_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_pregnancies_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_pregnancies_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_pregnancies_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_pregnancies_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_pregnancies_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_pregnancies_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_pregnancies_encounter_id ON clinical_pregnancies (encounter_id);

CREATE INDEX ix_clinical_pregnancies_facility_id ON clinical_pregnancies (facility_id);

CREATE INDEX ix_clinical_pregnancies_organization_id ON clinical_pregnancies (organization_id);

CREATE INDEX ix_clinical_pregnancies_patient_id ON clinical_pregnancies (patient_id);

CREATE INDEX ix_clinical_pregnancies_status ON clinical_pregnancies (status);


CREATE TABLE clinical_procedures (
	asset_id VARCHAR(64), 
	cssd_cycle_id VARCHAR(64), 
	procedure_name VARCHAR(200) NOT NULL, 
	room VARCHAR(80), 
	starts_at TIMESTAMP WITH TIME ZONE, 
	ends_at TIMESTAMP WITH TIME ZONE, 
	checklist TEXT, 
	checklist_verified_by VARCHAR(64), 
	anesthesia_record TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_procedures PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_procedures_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_clinical_procedures_cssd_cycle_id_cssd_cycles FOREIGN KEY(cssd_cycle_id) REFERENCES cssd_cycles (id), 
	CONSTRAINT fk_clinical_procedures_checklist_verified_by_users FOREIGN KEY(checklist_verified_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_procedures_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_procedures_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_procedures_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_procedures_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_procedures_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_procedures_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_procedures_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_procedures_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_procedures_encounter_id ON clinical_procedures (encounter_id);

CREATE INDEX ix_clinical_procedures_facility_id ON clinical_procedures (facility_id);

CREATE INDEX ix_clinical_procedures_organization_id ON clinical_procedures (organization_id);

CREATE INDEX ix_clinical_procedures_patient_id ON clinical_procedures (patient_id);

CREATE INDEX ix_clinical_procedures_status ON clinical_procedures (status);


CREATE TABLE clinical_referrals (
	destination VARCHAR(200) NOT NULL, 
	reason TEXT NOT NULL, 
	document_revision_id VARCHAR(64), 
	packet TEXT, 
	response_source VARCHAR(200), 
	response_note TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_referrals PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_referrals_document_revision_id_document_versions FOREIGN KEY(document_revision_id) REFERENCES document_versions (id), 
	CONSTRAINT fk_clinical_referrals_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_referrals_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_referrals_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_referrals_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_referrals_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_referrals_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_referrals_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_referrals_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_referrals_encounter_id ON clinical_referrals (encounter_id);

CREATE INDEX ix_clinical_referrals_facility_id ON clinical_referrals (facility_id);

CREATE INDEX ix_clinical_referrals_organization_id ON clinical_referrals (organization_id);

CREATE INDEX ix_clinical_referrals_patient_id ON clinical_referrals (patient_id);

CREATE INDEX ix_clinical_referrals_status ON clinical_referrals (status);


CREATE TABLE clinical_rehab (
	order_id VARCHAR(64) NOT NULL, 
	order_version INTEGER NOT NULL, 
	goals TEXT NOT NULL, 
	assessment TEXT, 
	therapist_id VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64), 
	status VARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_clinical_rehab PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_rehab_order_id_clinical_orders FOREIGN KEY(order_id) REFERENCES clinical_orders (id), 
	CONSTRAINT fk_clinical_rehab_therapist_id_users FOREIGN KEY(therapist_id) REFERENCES users (id), 
	CONSTRAINT fk_clinical_rehab_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_rehab_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_clinical_rehab_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_clinical_rehab_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_clinical_rehab_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
	CONSTRAINT fk_clinical_rehab_patient_scope FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT fk_clinical_rehab_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_clinical_rehab_positive_version CHECK (version > 0)
)

;

CREATE INDEX ix_clinical_rehab_encounter_id ON clinical_rehab (encounter_id);

CREATE INDEX ix_clinical_rehab_facility_id ON clinical_rehab (facility_id);

CREATE INDEX ix_clinical_rehab_organization_id ON clinical_rehab (organization_id);

CREATE INDEX ix_clinical_rehab_patient_id ON clinical_rehab (patient_id);

CREATE INDEX ix_clinical_rehab_status ON clinical_rehab (status);


CREATE TABLE clinical_slots (
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	label VARCHAR(200) NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	capacity INTEGER NOT NULL, 
	CONSTRAINT pk_clinical_slots PRIMARY KEY (id), 
	CONSTRAINT ck_clinical_slots_positive_capacity CHECK (capacity > 0), 
	CONSTRAINT fk_clinical_slots_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_clinical_slots_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_clinical_slots_organization_id ON clinical_slots (organization_id);


CREATE TABLE clinical_therapy_progress (
	id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	performed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	progress TEXT NOT NULL, 
	author_id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_clinical_therapy_progress PRIMARY KEY (id), 
	CONSTRAINT uq_clinical_therapy_progress_session_id UNIQUE (session_id), 
	CONSTRAINT fk_clinical_therapy_progress_session_id_clinical_therap_3b28 FOREIGN KEY(session_id) REFERENCES clinical_therapy_sessions (id), 
	CONSTRAINT fk_clinical_therapy_progress_author_id_users FOREIGN KEY(author_id) REFERENCES users (id)
)

;


CREATE TABLE clinical_therapy_sessions (
	id VARCHAR(64) NOT NULL, 
	plan_id VARCHAR(64) NOT NULL, 
	appointment_id VARCHAR(64) NOT NULL, 
	scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	author_id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_clinical_therapy_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_clinical_therapy_sessions_plan_id_clinical_rehab FOREIGN KEY(plan_id) REFERENCES clinical_rehab (id), 
	CONSTRAINT uq_clinical_therapy_sessions_appointment_id UNIQUE (appointment_id), 
	CONSTRAINT fk_clinical_therapy_sessions_appointment_id_clinical_ap_f522 FOREIGN KEY(appointment_id) REFERENCES clinical_appointments (id), 
	CONSTRAINT fk_clinical_therapy_sessions_author_id_users FOREIGN KEY(author_id) REFERENCES users (id)
)

;


CREATE TABLE committed_results (
	proposal_id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	action_hash VARCHAR(64) NOT NULL, 
	action_canonical TEXT NOT NULL, 
	operation_key VARCHAR(120) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_committed_results PRIMARY KEY (id), 
	CONSTRAINT uq_committed_results_proposal_id UNIQUE (proposal_id), 
	CONSTRAINT fk_committed_results_proposal_id_proposals FOREIGN KEY(proposal_id) REFERENCES proposals (id), 
	CONSTRAINT uq_committed_results_task_id UNIQUE (task_id), 
	CONSTRAINT fk_committed_results_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_committed_results_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE connector_attempts (
	binding_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	operation VARCHAR(24) NOT NULL, 
	operation_key VARCHAR(120) NOT NULL, 
	request_id VARCHAR(64) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	authorization_hash VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	lease_id VARCHAR(64) NOT NULL, 
	lease_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	response JSONB, 
	error_code VARCHAR(64), 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_connector_attempts PRIMARY KEY (id), 
	CONSTRAINT uq_connector_attempt_actor_session_key UNIQUE (actor_id, session_id, operation_key), 
	CONSTRAINT ck_connector_attempts_attempt_operation CHECK (operation IN ('import','read','confirm')), 
	CONSTRAINT ck_connector_attempts_attempt_status CHECK (status IN ('running','succeeded','unknown','rejected','quarantined')), 
	CONSTRAINT fk_connector_attempts_binding_id_connector_bindings FOREIGN KEY(binding_id) REFERENCES connector_bindings (id), 
	CONSTRAINT fk_connector_attempts_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_connector_attempts_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), 
	CONSTRAINT uq_connector_attempts_request_id UNIQUE (request_id)
)

;

CREATE INDEX ix_connector_attempts_binding_id ON connector_attempts (binding_id);


CREATE TABLE connector_bindings (
	connector VARCHAR(24) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	task_id VARCHAR(64) NOT NULL, 
	source_id VARCHAR(64) NOT NULL, 
	source_version INTEGER NOT NULL, 
	source_hash VARCHAR(64) NOT NULL, 
	source_snapshot JSONB NOT NULL, 
	lab_values JSONB NOT NULL, 
	external_report_id VARCHAR(128), 
	state VARCHAR(24) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_connector_bindings PRIMARY KEY (id), 
	CONSTRAINT uq_connector_binding_source UNIQUE (actor_id, session_id, connector, task_id, source_id, source_version), 
	CONSTRAINT fk_connector_binding_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT ck_connector_bindings_positive_source_version CHECK (source_version > 0), 
	CONSTRAINT ck_connector_bindings_known_connector CHECK (connector = 'labclear'), 
	CONSTRAINT ck_connector_bindings_binding_state CHECK (state IN ('reserved','draft','confirmed','unknown','quarantined')), 
	CONSTRAINT fk_connector_bindings_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_connector_bindings_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_connector_bindings_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_connector_bindings_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), 
	CONSTRAINT fk_connector_bindings_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_connector_bindings_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_connector_bindings_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_connector_bindings_source_id_clinical_labs FOREIGN KEY(source_id) REFERENCES clinical_labs (id)
)

;


CREATE TABLE connector_exchanges (
	attempt_id VARCHAR(64) NOT NULL, 
	context_snapshot JSONB NOT NULL, 
	outcome VARCHAR(24) NOT NULL, 
	receipt JSONB, 
	error_code VARCHAR(64), 
	quarantined BOOLEAN NOT NULL, 
	quarantine_reason VARCHAR(64), 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_connector_exchanges PRIMARY KEY (id), 
	CONSTRAINT ck_connector_exchanges_exchange_outcome CHECK (outcome IN ('running','succeeded','unknown','rejected')), 
	CONSTRAINT fk_connector_exchanges_attempt_id_connector_attempts FOREIGN KEY(attempt_id) REFERENCES connector_attempts (id)
)

;

CREATE INDEX ix_connector_exchanges_attempt_id ON connector_exchanges (attempt_id);


CREATE TABLE corrective_actions (
	incident_id VARCHAR(64) NOT NULL, 
	owner_id VARCHAR(64) NOT NULL, 
	action_plan TEXT NOT NULL, 
	evidence TEXT, 
	reviewer_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_corrective_actions PRIMARY KEY (id), 
	CONSTRAINT uq_corrective_actions_incident_id UNIQUE (incident_id), 
	CONSTRAINT fk_corrective_actions_incident_id_incidents FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	CONSTRAINT fk_corrective_actions_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), 
	CONSTRAINT fk_corrective_actions_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id), 
	CONSTRAINT fk_corrective_actions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_corrective_actions_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_corrective_actions_facility_id ON corrective_actions (facility_id);

CREATE INDEX ix_corrective_actions_organization_id ON corrective_actions (organization_id);


CREATE TABLE cost_entries (
	encounter_id VARCHAR(64), 
	department_id VARCHAR(64), 
	source_movement_id VARCHAR(64), 
	label VARCHAR(200) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	method_version VARCHAR(100) NOT NULL, 
	original_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_cost_entries PRIMARY KEY (id), 
	CONSTRAINT fk_cost_entries_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_cost_entries_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
	CONSTRAINT fk_cost_entries_source_movement_id_stock_movements FOREIGN KEY(source_movement_id) REFERENCES stock_movements (id), 
	CONSTRAINT fk_cost_entries_original_id_cost_entries FOREIGN KEY(original_id) REFERENCES cost_entries (id), 
	CONSTRAINT fk_cost_entries_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_cost_entries_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_cost_entries_facility_id ON cost_entries (facility_id);

CREATE INDEX ix_cost_entries_organization_id ON cost_entries (organization_id);


CREATE TABLE coverage_records (
	patient_id VARCHAR(64) NOT NULL, 
	payer_name VARCHAR(200) NOT NULL, 
	evidence TEXT NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_coverage_records PRIMARY KEY (id), 
	CONSTRAINT fk_coverage_records_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_coverage_records_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_coverage_records_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_coverage_records_facility_id ON coverage_records (facility_id);

CREATE INDEX ix_coverage_records_organization_id ON coverage_records (organization_id);

CREATE INDEX ix_coverage_records_patient_id ON coverage_records (patient_id);


CREATE TABLE cssd_cycles (
	asset_id VARCHAR(64) NOT NULL, 
	operator_id VARCHAR(64) NOT NULL, 
	cycle_code VARCHAR(100) NOT NULL, 
	evidence TEXT, 
	reviewer_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_cssd_cycles PRIMARY KEY (id), 
	CONSTRAINT fk_cssd_cycles_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_cssd_cycles_operator_id_users FOREIGN KEY(operator_id) REFERENCES users (id), 
	CONSTRAINT fk_cssd_cycles_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id), 
	CONSTRAINT fk_cssd_cycles_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_cssd_cycles_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_cssd_cycles_facility_id ON cssd_cycles (facility_id);

CREATE INDEX ix_cssd_cycles_organization_id ON cssd_cycles (organization_id);


CREATE TABLE dataset_access (
	dataset_id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	granted_by VARCHAR(64) NOT NULL, 
	purpose TEXT NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dataset_access PRIMARY KEY (id), 
	CONSTRAINT uq_dataset_access_dataset_id_user_id UNIQUE (dataset_id, user_id), 
	CONSTRAINT fk_dataset_access_dataset_id_dataset_versions FOREIGN KEY(dataset_id) REFERENCES dataset_versions (id), 
	CONSTRAINT fk_dataset_access_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_dataset_access_granted_by_users FOREIGN KEY(granted_by) REFERENCES users (id), 
	CONSTRAINT fk_dataset_access_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dataset_access_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_dataset_access_dataset_id ON dataset_access (dataset_id);

CREATE INDEX ix_dataset_access_facility_id ON dataset_access (facility_id);

CREATE INDEX ix_dataset_access_organization_id ON dataset_access (organization_id);


CREATE TABLE dataset_rows (
	id VARCHAR(64) NOT NULL, 
	dataset_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	source_version INTEGER NOT NULL, 
	partition VARCHAR(10) NOT NULL, 
	snapshot JSONB NOT NULL, 
	CONSTRAINT pk_dataset_rows PRIMARY KEY (id), 
	CONSTRAINT uq_dataset_rows_dataset_id_encounter_id UNIQUE (dataset_id, encounter_id), 
	CONSTRAINT ck_dataset_rows_erp_check_12 CHECK (partition IN ('train','test')), 
	CONSTRAINT fk_dataset_rows_dataset_id_dataset_versions FOREIGN KEY(dataset_id) REFERENCES dataset_versions (id), 
	CONSTRAINT fk_dataset_rows_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_dataset_rows_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id)
)

;

CREATE INDEX ix_dataset_rows_dataset_id ON dataset_rows (dataset_id);


CREATE TABLE dataset_versions (
	name VARCHAR(200) NOT NULL, 
	encounter_kind VARCHAR(30) NOT NULL, 
	definition_version VARCHAR(50) NOT NULL, 
	snapshot_hash VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dataset_versions PRIMARY KEY (id), 
	CONSTRAINT fk_dataset_versions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dataset_versions_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_dataset_versions_facility_id ON dataset_versions (facility_id);

CREATE INDEX ix_dataset_versions_organization_id ON dataset_versions (organization_id);


CREATE TABLE delivery_attempts (
	message_id VARCHAR(64) NOT NULL, 
	outcome VARCHAR(40) NOT NULL, 
	adapter VARCHAR(50) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_delivery_attempts PRIMARY KEY (id), 
	CONSTRAINT fk_delivery_attempts_message_id_integration_messages FOREIGN KEY(message_id) REFERENCES integration_messages (id), 
	CONSTRAINT fk_delivery_attempts_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_delivery_attempts_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_delivery_attempts_facility_id ON delivery_attempts (facility_id);

CREATE INDEX ix_delivery_attempts_message_id ON delivery_attempts (message_id);

CREATE INDEX ix_delivery_attempts_organization_id ON delivery_attempts (organization_id);


CREATE TABLE departments (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_departments PRIMARY KEY (id), 
	CONSTRAINT fk_departments_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_departments_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;


CREATE TABLE document_attestations (
	document_version_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_document_attestations PRIMARY KEY (id), 
	CONSTRAINT uq_document_attestations_document_version_id UNIQUE (document_version_id), 
	CONSTRAINT fk_document_attestations_document_version_id_document_versions FOREIGN KEY(document_version_id) REFERENCES document_versions (id), 
	CONSTRAINT fk_document_attestations_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE document_versions (
	document_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	reason TEXT, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_document_versions PRIMARY KEY (id), 
	CONSTRAINT uq_document_versions_document_id_version UNIQUE (document_id, version), 
	CONSTRAINT uq_document_versions_id_document_id UNIQUE (id, document_id), 
	CONSTRAINT fk_document_versions_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id), 
	CONSTRAINT fk_document_versions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
)

;

CREATE INDEX ix_document_versions_document_id ON document_versions (document_id);


CREATE TABLE documents (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	title VARCHAR(240) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	version INTEGER NOT NULL, 
	current_version_id VARCHAR(64), 
	published BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_documents PRIMARY KEY (id), 
	CONSTRAINT fk_documents_encounter_id_patient_id_organization_id_fa_acc3 FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT fk_documents_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_documents_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_documents_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_documents_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id)
)

;

CREATE INDEX ix_documents_encounter_id ON documents (encounter_id);

CREATE INDEX ix_documents_facility_id ON documents (facility_id);

CREATE INDEX ix_documents_organization_id ON documents (organization_id);

CREATE INDEX ix_documents_patient_id ON documents (patient_id);


CREATE TABLE dr_attempts (
	binding_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	operation VARCHAR(24) NOT NULL, 
	operation_key VARCHAR(120) NOT NULL, 
	request_id VARCHAR(64) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	authorization_hash VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	lease_id VARCHAR(64) NOT NULL, 
	lease_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	response JSONB, 
	error_code VARCHAR(64), 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_attempts PRIMARY KEY (id), 
	CONSTRAINT uq_dr_attempt_actor_session_key UNIQUE (actor_id, session_id, operation_key), 
	CONSTRAINT ck_dr_attempts_attempt_operation CHECK (operation IN ('import','dispatch','read_report')), 
	CONSTRAINT ck_dr_attempts_attempt_status CHECK (status IN ('running','succeeded','unknown','rejected','quarantined')), 
	CONSTRAINT fk_dr_attempts_binding_id_dr_bindings FOREIGN KEY(binding_id) REFERENCES dr_bindings (id), 
	CONSTRAINT fk_dr_attempts_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_dr_attempts_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), 
	CONSTRAINT uq_dr_attempts_request_id UNIQUE (request_id)
)

;

CREATE INDEX ix_dr_attempts_binding_id ON dr_attempts (binding_id);


CREATE TABLE dr_bindings (
	source_set_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	destination_id VARCHAR(64) NOT NULL, 
	destination_sha256 VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	consent_snapshot JSONB NOT NULL, 
	state VARCHAR(24) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_bindings PRIMARY KEY (id), 
	CONSTRAINT fk_dr_binding_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT uq_dr_binding_set_actor_session UNIQUE (source_set_id, actor_id, session_id), 
	CONSTRAINT ck_dr_bindings_binding_state CHECK (state IN ('reserved','imported','unknown','quarantined')), 
	CONSTRAINT fk_dr_bindings_source_set_id_dr_source_sets FOREIGN KEY(source_set_id) REFERENCES dr_source_sets (id), 
	CONSTRAINT fk_dr_bindings_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_dr_bindings_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), 
	CONSTRAINT fk_dr_bindings_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dr_bindings_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_dr_bindings_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_dr_bindings_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id)
)

;


CREATE TABLE dr_capability_grant_events (
	grant_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	grant_version INTEGER NOT NULL, 
	operation VARCHAR(16) NOT NULL, 
	old_snapshot JSONB, 
	new_snapshot JSONB NOT NULL, 
	database_principal VARCHAR(128) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_capability_grant_events PRIMARY KEY (id), 
	CONSTRAINT uq_dr_grant_event_version UNIQUE (grant_id, grant_version), 
	CONSTRAINT ck_dr_capability_grant_events_grant_event_operation CHECK (operation IN ('INSERT','UPDATE') AND grant_version > 0), 
	CONSTRAINT fk_dr_capability_grant_events_grant_id_dr_capability_grants FOREIGN KEY(grant_id) REFERENCES dr_capability_grants (id), 
	CONSTRAINT fk_dr_capability_grant_events_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dr_capability_grant_events_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_dr_capability_grant_events_grant_id ON dr_capability_grant_events (grant_id);


CREATE TABLE dr_capability_grants (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	capability VARCHAR(32) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	valid_from TIMESTAMP WITH TIME ZONE NOT NULL, 
	valid_until TIMESTAMP WITH TIME ZONE NOT NULL, 
	verification_status VARCHAR(16) NOT NULL, 
	evidence_reference VARCHAR(240) NOT NULL, 
	verifier_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_capability_grants PRIMARY KEY (id), 
	CONSTRAINT fk_dr_grant_facility_scope FOREIGN KEY(facility_id, organization_id) REFERENCES facilities (id, organization_id), 
	CONSTRAINT ck_dr_capability_grants_explicit_clinical_capability CHECK (capability IN ('dr.grade.confirm','dr.report.sign')), 
	CONSTRAINT ck_dr_capability_grants_verified_grant_state CHECK (status IN ('active','revoked') AND verification_status='verified'), 
	CONSTRAINT ck_dr_capability_grants_valid_grant_interval CHECK (valid_until > valid_from AND version > 0), 
	CONSTRAINT fk_dr_capability_grants_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dr_capability_grants_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_dr_capability_grants_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_dr_capability_grants_verifier_id_users FOREIGN KEY(verifier_id) REFERENCES users (id)
)

;


CREATE TABLE dr_exchanges (
	attempt_id VARCHAR(64) NOT NULL, 
	context_snapshot JSONB NOT NULL, 
	outcome VARCHAR(24) NOT NULL, 
	receipt JSONB, 
	error_code VARCHAR(64), 
	quarantined BOOLEAN NOT NULL, 
	quarantine_reason VARCHAR(64), 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_exchanges PRIMARY KEY (id), 
	CONSTRAINT ck_dr_exchanges_exchange_outcome CHECK (outcome IN ('running','succeeded','unknown','rejected')), 
	CONSTRAINT fk_dr_exchanges_attempt_id_dr_attempts FOREIGN KEY(attempt_id) REFERENCES dr_attempts (id)
)

;

CREATE INDEX ix_dr_exchanges_attempt_id ON dr_exchanges (attempt_id);


CREATE TABLE dr_report_receipts (
	binding_id VARCHAR(64) NOT NULL, 
	attempt_id VARCHAR(64) NOT NULL, 
	source_set_id VARCHAR(64) NOT NULL, 
	case_id VARCHAR(64) NOT NULL, 
	case_revision INTEGER NOT NULL, 
	snapshot_sha256 VARCHAR(64) NOT NULL, 
	receipt JSONB NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_report_receipts PRIMARY KEY (id), 
	CONSTRAINT fk_dr_report_receipts_binding_id_dr_bindings FOREIGN KEY(binding_id) REFERENCES dr_bindings (id), 
	CONSTRAINT uq_dr_report_receipts_attempt_id UNIQUE (attempt_id), 
	CONSTRAINT fk_dr_report_receipts_attempt_id_dr_attempts FOREIGN KEY(attempt_id) REFERENCES dr_attempts (id), 
	CONSTRAINT fk_dr_report_receipts_source_set_id_dr_source_sets FOREIGN KEY(source_set_id) REFERENCES dr_source_sets (id)
)

;


CREATE TABLE dr_source_provenance (
	source_id VARCHAR(64) NOT NULL, 
	source_version INTEGER NOT NULL, 
	image_sha256 VARCHAR(64) NOT NULL, 
	byte_size INTEGER NOT NULL, 
	source_origin VARCHAR(24) NOT NULL, 
	laterality VARCHAR(1) NOT NULL, 
	modality VARCHAR(8) NOT NULL, 
	capture_time VARCHAR(32), 
	evidence_reference VARCHAR(240) NOT NULL, 
	dataset_provenance JSONB, 
	registrar_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_source_provenance PRIMARY KEY (id), 
	CONSTRAINT fk_dr_provenance_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT uq_dr_provenance_source_revision UNIQUE (source_id, source_version), 
	CONSTRAINT ck_dr_source_provenance_registered_source_origin CHECK ((source_origin='SYNTHETIC' AND dataset_provenance IS NULL) OR (source_origin='PUBLIC' AND dataset_provenance IS NOT NULL AND jsonb_typeof(dataset_provenance)='object')), 
	CONSTRAINT ck_dr_source_provenance_explicit_eye_modality CHECK (laterality IN ('L','R') AND modality IN ('CFP','UWF')), 
	CONSTRAINT ck_dr_source_provenance_source_size_revision CHECK (source_version > 0 AND byte_size BETWEEN 1 AND 1048576), 
	CONSTRAINT fk_dr_source_provenance_source_id_clinical_imaging FOREIGN KEY(source_id) REFERENCES clinical_imaging (id), 
	CONSTRAINT fk_dr_source_provenance_registrar_id_users FOREIGN KEY(registrar_id) REFERENCES users (id), 
	CONSTRAINT fk_dr_source_provenance_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dr_source_provenance_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_dr_source_provenance_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_dr_source_provenance_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id)
)

;


CREATE TABLE dr_source_set_items (
	source_set_id VARCHAR(64) NOT NULL, 
	position INTEGER NOT NULL, 
	source_id VARCHAR(64) NOT NULL, 
	source_version INTEGER NOT NULL, 
	provenance_id VARCHAR(64) NOT NULL, 
	source_snapshot JSONB NOT NULL, 
	source_sha256 VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_dr_source_set_items PRIMARY KEY (id), 
	CONSTRAINT uq_dr_item_position UNIQUE (source_set_id, position), 
	CONSTRAINT uq_dr_item_source UNIQUE (source_set_id, source_id), 
	CONSTRAINT ck_dr_source_set_items_bounded_position_revision CHECK (position BETWEEN 0 AND 7 AND source_version > 0), 
	CONSTRAINT fk_dr_source_set_items_source_set_id_dr_source_sets FOREIGN KEY(source_set_id) REFERENCES dr_source_sets (id), 
	CONSTRAINT fk_dr_source_set_items_source_id_clinical_imaging FOREIGN KEY(source_id) REFERENCES clinical_imaging (id), 
	CONSTRAINT fk_dr_source_set_items_provenance_id_dr_source_provenance FOREIGN KEY(provenance_id) REFERENCES dr_source_provenance (id)
)

;


CREATE TABLE dr_source_sets (
	task_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	session_id VARCHAR(64) NOT NULL, 
	operation_key VARCHAR(120) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	revision INTEGER NOT NULL, 
	manifest_sha256 VARCHAR(64) NOT NULL, 
	manifest JSONB NOT NULL, 
	consent_snapshot JSONB NOT NULL, 
	destination_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_dr_source_sets PRIMARY KEY (id), 
	CONSTRAINT fk_dr_set_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT uq_dr_set_actor_session_key UNIQUE (actor_id, session_id, operation_key), 
	CONSTRAINT ck_dr_source_sets_positive_revision CHECK (revision > 0), 
	CONSTRAINT fk_dr_source_sets_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_dr_source_sets_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), 
	CONSTRAINT fk_dr_source_sets_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), 
	CONSTRAINT fk_dr_source_sets_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_dr_source_sets_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_dr_source_sets_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_dr_source_sets_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id)
)

;


CREATE TABLE encounters (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	department_id VARCHAR(64), 
	practitioner_id VARCHAR(64), 
	kind VARCHAR(24) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	version INTEGER NOT NULL, 
	disposition TEXT, 
	published BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_encounters PRIMARY KEY (id), 
	CONSTRAINT uq_encounters_id_patient_id_organization_id_facility_id UNIQUE (id, patient_id, organization_id, facility_id), 
	CONSTRAINT fk_encounters_patient_id_organization_id_facility_id_patients FOREIGN KEY(patient_id, organization_id, facility_id) REFERENCES patients (id, organization_id, facility_id), 
	CONSTRAINT ck_encounters_positive_version CHECK (version > 0), 
	CONSTRAINT fk_encounters_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_encounters_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_encounters_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_encounters_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
	CONSTRAINT fk_encounters_practitioner_id_users FOREIGN KEY(practitioner_id) REFERENCES users (id)
)

;

CREATE INDEX ix_encounters_facility_id ON encounters (facility_id);

CREATE INDEX ix_encounters_organization_id ON encounters (organization_id);

CREATE INDEX ix_encounters_patient_id ON encounters (patient_id);


CREATE TABLE equipment_assets (
	name VARCHAR(200) NOT NULL, 
	location_id VARCHAR(64) NOT NULL, 
	department_id VARCHAR(64), 
	maintenance_due DATE, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_equipment_assets PRIMARY KEY (id), 
	CONSTRAINT fk_equipment_assets_location_id_locations FOREIGN KEY(location_id) REFERENCES locations (id), 
	CONSTRAINT fk_equipment_assets_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
	CONSTRAINT fk_equipment_assets_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_equipment_assets_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_equipment_assets_facility_id ON equipment_assets (facility_id);

CREATE INDEX ix_equipment_assets_organization_id ON equipment_assets (organization_id);


CREATE TABLE facilities (
	organization_id VARCHAR(64) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_facilities PRIMARY KEY (id), 
	CONSTRAINT uq_facilities_id_organization_id UNIQUE (id, organization_id), 
	CONSTRAINT fk_facilities_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE INDEX ix_facilities_organization_id ON facilities (organization_id);


CREATE TABLE facility_work_orders (
	location_id VARCHAR(64) NOT NULL, 
	description TEXT NOT NULL, 
	assignee_id VARCHAR(64), 
	evidence TEXT, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_facility_work_orders PRIMARY KEY (id), 
	CONSTRAINT fk_facility_work_orders_location_id_locations FOREIGN KEY(location_id) REFERENCES locations (id), 
	CONSTRAINT fk_facility_work_orders_assignee_id_users FOREIGN KEY(assignee_id) REFERENCES users (id), 
	CONSTRAINT fk_facility_work_orders_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_facility_work_orders_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_facility_work_orders_facility_id ON facility_work_orders (facility_id);

CREATE INDEX ix_facility_work_orders_organization_id ON facility_work_orders (organization_id);


CREATE TABLE goods_receipts (
	purchase_id VARCHAR(64) NOT NULL, 
	lot_id VARCHAR(64) NOT NULL, 
	movement_id VARCHAR(64) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	receipt_key VARCHAR(160) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_goods_receipts PRIMARY KEY (id), 
	CONSTRAINT uq_goods_receipts_organization_id_receipt_key UNIQUE (organization_id, receipt_key), 
	CONSTRAINT fk_goods_receipts_purchase_id_purchases FOREIGN KEY(purchase_id) REFERENCES purchases (id), 
	CONSTRAINT fk_goods_receipts_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT uq_goods_receipts_movement_id UNIQUE (movement_id), 
	CONSTRAINT fk_goods_receipts_movement_id_stock_movements FOREIGN KEY(movement_id) REFERENCES stock_movements (id), 
	CONSTRAINT fk_goods_receipts_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_goods_receipts_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_goods_receipts_facility_id ON goods_receipts (facility_id);

CREATE INDEX ix_goods_receipts_organization_id ON goods_receipts (organization_id);

CREATE INDEX ix_goods_receipts_purchase_id ON goods_receipts (purchase_id);


CREATE TABLE human_reviews (
	proposal_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	action_hash VARCHAR(64) NOT NULL, 
	decision VARCHAR(24) NOT NULL, 
	edited_text TEXT, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_human_reviews PRIMARY KEY (id), 
	CONSTRAINT fk_human_reviews_proposal_id_proposals FOREIGN KEY(proposal_id) REFERENCES proposals (id), 
	CONSTRAINT fk_human_reviews_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_human_reviews_proposal_id ON human_reviews (proposal_id);


CREATE TABLE incidents (
	encounter_id VARCHAR(64), 
	asset_id VARCHAR(64), 
	reporter_id VARCHAR(64) NOT NULL, 
	description TEXT NOT NULL, 
	classification VARCHAR(100), 
	case_definition_version VARCHAR(100), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_incidents PRIMARY KEY (id), 
	CONSTRAINT fk_incidents_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_incidents_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_incidents_reporter_id_users FOREIGN KEY(reporter_id) REFERENCES users (id), 
	CONSTRAINT fk_incidents_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_incidents_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_incidents_facility_id ON incidents (facility_id);

CREATE INDEX ix_incidents_organization_id ON incidents (organization_id);


CREATE TABLE inference_runs (
	task_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	provider VARCHAR(64) NOT NULL, 
	outcome VARCHAR(24) NOT NULL, 
	reason TEXT, 
	elapsed_ms INTEGER NOT NULL, 
	measured_cost NUMERIC(18, 6), 
	usage JSONB, 
	operation_key VARCHAR(120), 
	request_hash VARCHAR(64), 
	authorization_hash VARCHAR(64), 
	context_snapshot JSONB, 
	provenance JSONB, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_inference_runs PRIMARY KEY (id), 
	CONSTRAINT uq_inference_runs_actor_id_operation_key UNIQUE (actor_id, operation_key), 
	CONSTRAINT fk_inference_runs_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_inference_runs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_inference_runs_task_id ON inference_runs (task_id);


CREATE TABLE integration_messages (
	source_id VARCHAR(160) NOT NULL, 
	sequence INTEGER NOT NULL, 
	contract_version VARCHAR(100) NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	source_record_id VARCHAR(64) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	error VARCHAR(300), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_integration_messages PRIMARY KEY (id), 
	CONSTRAINT uq_integration_messages_organization_id_source_id_sequence UNIQUE (organization_id, source_id, sequence), 
	CONSTRAINT fk_integration_messages_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_integration_messages_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_integration_messages_facility_id ON integration_messages (facility_id);

CREATE INDEX ix_integration_messages_organization_id ON integration_messages (organization_id);


CREATE TABLE integration_receipts (
	message_id VARCHAR(64) NOT NULL, 
	source_record_id VARCHAR(64) NOT NULL, 
	receipt_kind VARCHAR(40) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_integration_receipts PRIMARY KEY (id), 
	CONSTRAINT uq_integration_receipts_message_id UNIQUE (message_id), 
	CONSTRAINT fk_integration_receipts_message_id_integration_messages FOREIGN KEY(message_id) REFERENCES integration_messages (id), 
	CONSTRAINT fk_integration_receipts_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_integration_receipts_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_integration_receipts_facility_id ON integration_receipts (facility_id);

CREATE INDEX ix_integration_receipts_organization_id ON integration_receipts (organization_id);


CREATE TABLE inventory_items (
	name VARCHAR(200) NOT NULL, 
	unit VARCHAR(30) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_inventory_items PRIMARY KEY (id), 
	CONSTRAINT fk_inventory_items_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_inventory_items_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_inventory_items_facility_id ON inventory_items (facility_id);

CREATE INDEX ix_inventory_items_organization_id ON inventory_items (organization_id);


CREATE TABLE inventory_lots (
	item_id VARCHAR(64) NOT NULL, 
	lot_number VARCHAR(100) NOT NULL, 
	expiry_date DATE NOT NULL, 
	unit_cost NUMERIC(18, 2) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_inventory_lots PRIMARY KEY (id), 
	CONSTRAINT uq_inventory_lots_organization_id_item_id_lot_number UNIQUE (organization_id, item_id, lot_number), 
	CONSTRAINT ck_inventory_lots_erp_check_8 CHECK (unit_cost >= 0), 
	CONSTRAINT fk_inventory_lots_item_id_inventory_items FOREIGN KEY(item_id) REFERENCES inventory_items (id), 
	CONSTRAINT fk_inventory_lots_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_inventory_lots_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_inventory_lots_facility_id ON inventory_lots (facility_id);

CREATE INDEX ix_inventory_lots_organization_id ON inventory_lots (organization_id);


CREATE TABLE invoice_adjustments (
	invoice_id VARCHAR(64) NOT NULL, 
	original_charge_id VARCHAR(64) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	reason TEXT NOT NULL, 
	approver_id VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_invoice_adjustments PRIMARY KEY (id), 
	CONSTRAINT fk_invoice_adjustments_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	CONSTRAINT fk_invoice_adjustments_original_charge_id_charges FOREIGN KEY(original_charge_id) REFERENCES charges (id), 
	CONSTRAINT fk_invoice_adjustments_approver_id_users FOREIGN KEY(approver_id) REFERENCES users (id), 
	CONSTRAINT fk_invoice_adjustments_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_invoice_adjustments_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_invoice_adjustments_facility_id ON invoice_adjustments (facility_id);

CREATE INDEX ix_invoice_adjustments_invoice_id ON invoice_adjustments (invoice_id);

CREATE INDEX ix_invoice_adjustments_organization_id ON invoice_adjustments (organization_id);


CREATE TABLE invoices (
	encounter_id VARCHAR(64) NOT NULL, 
	label VARCHAR(200) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	billed NUMERIC(18, 2) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_invoices PRIMARY KEY (id), 
	CONSTRAINT fk_invoices_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_invoices_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_invoices_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_invoices_encounter_id ON invoices (encounter_id);

CREATE INDEX ix_invoices_facility_id ON invoices (facility_id);

CREATE INDEX ix_invoices_organization_id ON invoices (organization_id);


CREATE TABLE ledger_entries (
	source_id VARCHAR(100) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	original_entry_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_ledger_entries PRIMARY KEY (id), 
	CONSTRAINT uq_ledger_entries_source_id UNIQUE (source_id), 
	CONSTRAINT fk_ledger_entries_original_entry_id_ledger_entries FOREIGN KEY(original_entry_id) REFERENCES ledger_entries (id), 
	CONSTRAINT fk_ledger_entries_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_ledger_entries_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_ledger_entries_facility_id ON ledger_entries (facility_id);

CREATE INDEX ix_ledger_entries_organization_id ON ledger_entries (organization_id);


CREATE TABLE ledger_lines (
	id VARCHAR(64) NOT NULL, 
	entry_id VARCHAR(64) NOT NULL, 
	account VARCHAR(80) NOT NULL, 
	debit NUMERIC(18, 2) NOT NULL, 
	credit NUMERIC(18, 2) NOT NULL, 
	CONSTRAINT pk_ledger_lines PRIMARY KEY (id), 
	CONSTRAINT ck_ledger_lines_erp_check_6 CHECK (debit >= 0 AND credit >= 0 AND (debit = 0 OR credit = 0)), 
	CONSTRAINT fk_ledger_lines_entry_id_ledger_entries FOREIGN KEY(entry_id) REFERENCES ledger_entries (id)
)

;

CREATE INDEX ix_ledger_lines_entry_id ON ledger_lines (entry_id);


CREATE TABLE legacy_imports (
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	source_sha256 VARCHAR(64) NOT NULL, 
	mapping_sha256 VARCHAR(64) NOT NULL, 
	source_name VARCHAR(255) NOT NULL, 
	report_json TEXT NOT NULL, 
	created_by VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_legacy_imports PRIMARY KEY (id), 
	CONSTRAINT uq_legacy_imports_organization_id_facility_id_source_sha256 UNIQUE (organization_id, facility_id, source_sha256), 
	CONSTRAINT fk_legacy_imports_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_legacy_imports_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_legacy_imports_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
)

;

CREATE INDEX ix_legacy_imports_facility_id ON legacy_imports (facility_id);

CREATE INDEX ix_legacy_imports_organization_id ON legacy_imports (organization_id);


CREATE TABLE legacy_rows (
	id VARCHAR(64) NOT NULL, 
	import_id VARCHAR(64) NOT NULL, 
	source_table VARCHAR(40) NOT NULL, 
	legacy_id TEXT NOT NULL, 
	legacy_patient_id VARCHAR(255), 
	mapped_patient_id VARCHAR(64), 
	source_row_json TEXT NOT NULL, 
	row_sha256 VARCHAR(64) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	gap_json TEXT NOT NULL, 
	CONSTRAINT pk_legacy_rows PRIMARY KEY (id), 
	CONSTRAINT uq_legacy_rows_import_id_source_table_legacy_id UNIQUE (import_id, source_table, legacy_id), 
	CONSTRAINT fk_legacy_rows_import_id_legacy_imports FOREIGN KEY(import_id) REFERENCES legacy_imports (id), 
	CONSTRAINT fk_legacy_rows_mapped_patient_id_patients FOREIGN KEY(mapped_patient_id) REFERENCES patients (id)
)

;

CREATE INDEX ix_legacy_rows_import_id ON legacy_rows (import_id);

CREATE INDEX ix_legacy_rows_mapped_patient_id ON legacy_rows (mapped_patient_id);

CREATE INDEX ix_legacy_rows_source_table ON legacy_rows (source_table);


CREATE TABLE linen_dispatches (
	location_id VARCHAR(64) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	returned_quantity NUMERIC(18, 3) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_linen_dispatches PRIMARY KEY (id), 
	CONSTRAINT fk_linen_dispatches_location_id_locations FOREIGN KEY(location_id) REFERENCES locations (id), 
	CONSTRAINT fk_linen_dispatches_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_linen_dispatches_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_linen_dispatches_facility_id ON linen_dispatches (facility_id);

CREATE INDEX ix_linen_dispatches_organization_id ON linen_dispatches (organization_id);


CREATE TABLE locations (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_locations PRIMARY KEY (id), 
	CONSTRAINT fk_locations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_locations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;


CREATE TABLE login_attempts (
	identity_hash VARCHAR(64) NOT NULL, 
	successful BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_login_attempts PRIMARY KEY (id)
)

;

CREATE INDEX ix_login_attempts_identity_hash ON login_attempts (identity_hash);


CREATE TABLE maintenance_work_orders (
	asset_id VARCHAR(64) NOT NULL, 
	technician_id VARCHAR(64) NOT NULL, 
	evidence TEXT, 
	verifier_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_maintenance_work_orders PRIMARY KEY (id), 
	CONSTRAINT fk_maintenance_work_orders_asset_id_equipment_assets FOREIGN KEY(asset_id) REFERENCES equipment_assets (id), 
	CONSTRAINT fk_maintenance_work_orders_technician_id_users FOREIGN KEY(technician_id) REFERENCES users (id), 
	CONSTRAINT fk_maintenance_work_orders_verifier_id_users FOREIGN KEY(verifier_id) REFERENCES users (id), 
	CONSTRAINT fk_maintenance_work_orders_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_maintenance_work_orders_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_maintenance_work_orders_asset_id ON maintenance_work_orders (asset_id);

CREATE INDEX ix_maintenance_work_orders_facility_id ON maintenance_work_orders (facility_id);

CREATE INDEX ix_maintenance_work_orders_organization_id ON maintenance_work_orders (organization_id);


CREATE TABLE memberships (
	user_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	role VARCHAR(64) NOT NULL, 
	active BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_memberships PRIMARY KEY (id), 
	CONSTRAINT uq_memberships_user_id_facility_id_role UNIQUE (user_id, facility_id, role), 
	CONSTRAINT fk_memberships_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_memberships_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_memberships_role_roles FOREIGN KEY(role) REFERENCES roles (id)
)

;

CREATE INDEX ix_memberships_user_id ON memberships (user_id);


CREATE TABLE operational_jobs (
	id VARCHAR NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	command_kind VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	source_backup_id VARCHAR, 
	artifact_id VARCHAR, 
	result JSONB NOT NULL, 
	error_code VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_operational_jobs PRIMARY KEY (id), 
	CONSTRAINT ck_operational_jobs_allowed_command CHECK (command_kind IN ('backup','isolated_restore')), 
	CONSTRAINT ck_operational_jobs_allowed_status CHECK (status IN ('requested','running','completed','failed','restore_verified','restore_failed')), 
	CONSTRAINT fk_operational_jobs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_operational_jobs_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_operational_jobs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_operational_jobs_facility_id ON operational_jobs (facility_id);

CREATE INDEX ix_operational_jobs_organization_id ON operational_jobs (organization_id);


CREATE TABLE operations (
	authorization_hash VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	key VARCHAR(120) NOT NULL, 
	operation VARCHAR(180) NOT NULL, 
	payload_hash VARCHAR(64) NOT NULL, 
	response JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_operations PRIMARY KEY (actor_id, key), 
	CONSTRAINT fk_operations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_operations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_operations_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE order_revisions (
	order_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	instructions TEXT NOT NULL, 
	actor_id VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_order_revisions PRIMARY KEY (id), 
	CONSTRAINT uq_order_revisions_order_id_version UNIQUE (order_id, version), 
	CONSTRAINT fk_order_revisions_order_id_clinical_orders FOREIGN KEY(order_id) REFERENCES clinical_orders (id), 
	CONSTRAINT fk_order_revisions_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE organizations (
	name VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_organizations PRIMARY KEY (id)
)

;


CREATE TABLE patient_identifiers (
	patient_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	issuer VARCHAR(80) NOT NULL, 
	value VARCHAR(120) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_patient_identifiers PRIMARY KEY (id), 
	CONSTRAINT uq_patient_identifiers_organization_id_issuer_value UNIQUE (organization_id, issuer, value), 
	CONSTRAINT fk_patient_identifiers_patient_id_organization_id_patients FOREIGN KEY(patient_id, organization_id) REFERENCES patients (id, organization_id), 
	CONSTRAINT fk_patient_identifiers_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_patient_identifiers_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;


CREATE TABLE patients (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	display_name VARCHAR(200) NOT NULL, 
	birth_date DATE, 
	sex VARCHAR(16) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	version INTEGER NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_patients PRIMARY KEY (id), 
	CONSTRAINT uq_patients_id_organization_id_facility_id UNIQUE (id, organization_id, facility_id), 
	CONSTRAINT uq_patients_id_organization_id UNIQUE (id, organization_id), 
	CONSTRAINT fk_patients_facility_id_organization_id_facilities FOREIGN KEY(facility_id, organization_id) REFERENCES facilities (id, organization_id), 
	CONSTRAINT ck_patients_positive_version CHECK (version > 0), 
	CONSTRAINT fk_patients_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_patients_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_patients_facility_id ON patients (facility_id);

CREATE INDEX ix_patients_organization_id ON patients (organization_id);


CREATE TABLE payment_allocations (
	receipt_id VARCHAR(64) NOT NULL, 
	invoice_id VARCHAR(64) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_payment_allocations PRIMARY KEY (id), 
	CONSTRAINT uq_payment_allocations_receipt_id UNIQUE (receipt_id), 
	CONSTRAINT fk_payment_allocations_receipt_id_payment_receipts FOREIGN KEY(receipt_id) REFERENCES payment_receipts (id), 
	CONSTRAINT fk_payment_allocations_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	CONSTRAINT fk_payment_allocations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_payment_allocations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_payment_allocations_facility_id ON payment_allocations (facility_id);

CREATE INDEX ix_payment_allocations_invoice_id ON payment_allocations (invoice_id);

CREATE INDEX ix_payment_allocations_organization_id ON payment_allocations (organization_id);


CREATE TABLE payment_receipts (
	invoice_id VARCHAR(64) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	payer_name VARCHAR(200) NOT NULL, 
	recorded_by VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_payment_receipts PRIMARY KEY (id), 
	CONSTRAINT ck_payment_receipts_erp_check_4 CHECK (amount > 0), 
	CONSTRAINT fk_payment_receipts_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	CONSTRAINT fk_payment_receipts_recorded_by_users FOREIGN KEY(recorded_by) REFERENCES users (id), 
	CONSTRAINT fk_payment_receipts_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_payment_receipts_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_payment_receipts_facility_id ON payment_receipts (facility_id);

CREATE INDEX ix_payment_receipts_invoice_id ON payment_receipts (invoice_id);

CREATE INDEX ix_payment_receipts_organization_id ON payment_receipts (organization_id);


CREATE TABLE permissions (
	id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_permissions PRIMARY KEY (id)
)

;


CREATE TABLE price_versions (
	name VARCHAR(200) NOT NULL, 
	effective_from DATE NOT NULL, 
	unit_price NUMERIC(18, 2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_price_versions PRIMARY KEY (id), 
	CONSTRAINT ck_price_versions_erp_check_1 CHECK (unit_price >= 0), 
	CONSTRAINT fk_price_versions_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_price_versions_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_price_versions_facility_id ON price_versions (facility_id);

CREATE INDEX ix_price_versions_organization_id ON price_versions (organization_id);


CREATE TABLE proposal_versions (
	proposal_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	action_canonical TEXT NOT NULL, 
	action_hash VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_proposal_versions PRIMARY KEY (id), 
	CONSTRAINT uq_proposal_versions_proposal_id_version UNIQUE (proposal_id, version), 
	CONSTRAINT fk_proposal_versions_proposal_id_proposals FOREIGN KEY(proposal_id) REFERENCES proposals (id)
)

;


CREATE TABLE proposals (
	task_id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	document_version_id VARCHAR(64) NOT NULL, 
	encounter_version INTEGER NOT NULL, 
	task_version INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	action_canonical TEXT NOT NULL, 
	action_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_proposals PRIMARY KEY (id), 
	CONSTRAINT fk_proposals_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_proposals_run_id_inference_runs FOREIGN KEY(run_id) REFERENCES inference_runs (id), 
	CONSTRAINT fk_proposals_document_version_id_document_versions FOREIGN KEY(document_version_id) REFERENCES document_versions (id)
)

;

CREATE INDEX ix_proposals_task_id ON proposals (task_id);


CREATE TABLE purchases (
	supplier_id VARCHAR(64) NOT NULL, 
	item_id VARCHAR(64) NOT NULL, 
	department_id VARCHAR(64), 
	quantity NUMERIC(18, 3) NOT NULL, 
	received_quantity NUMERIC(18, 3) NOT NULL, 
	unit_price NUMERIC(18, 2) NOT NULL, 
	requested_by VARCHAR(64) NOT NULL, 
	approved_by VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_purchases PRIMARY KEY (id), 
	CONSTRAINT ck_purchases_erp_check_7 CHECK (quantity > 0 AND received_quantity >= 0 AND received_quantity <= quantity AND unit_price >= 0), 
	CONSTRAINT fk_purchases_supplier_id_suppliers FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	CONSTRAINT fk_purchases_item_id_inventory_items FOREIGN KEY(item_id) REFERENCES inventory_items (id), 
	CONSTRAINT fk_purchases_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
	CONSTRAINT fk_purchases_requested_by_users FOREIGN KEY(requested_by) REFERENCES users (id), 
	CONSTRAINT fk_purchases_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id), 
	CONSTRAINT fk_purchases_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_purchases_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_purchases_facility_id ON purchases (facility_id);

CREATE INDEX ix_purchases_organization_id ON purchases (organization_id);


CREATE TABLE reconciliation_tasks (
	message_id VARCHAR(64) NOT NULL, 
	integration_receipt_id VARCHAR(64) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_reconciliation_tasks PRIMARY KEY (id), 
	CONSTRAINT uq_reconciliation_tasks_message_id UNIQUE (message_id), 
	CONSTRAINT fk_reconciliation_tasks_message_id_integration_messages FOREIGN KEY(message_id) REFERENCES integration_messages (id), 
	CONSTRAINT fk_reconciliation_tasks_integration_receipt_id_integrat_4149 FOREIGN KEY(integration_receipt_id) REFERENCES integration_receipts (id), 
	CONSTRAINT fk_reconciliation_tasks_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_reconciliation_tasks_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_reconciliation_tasks_facility_id ON reconciliation_tasks (facility_id);

CREATE INDEX ix_reconciliation_tasks_organization_id ON reconciliation_tasks (organization_id);


CREATE TABLE refunds (
	receipt_id VARCHAR(64) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	reason TEXT NOT NULL, 
	requested_by VARCHAR(64) NOT NULL, 
	approved_by VARCHAR(64), 
	release_allocation BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_refunds PRIMARY KEY (id), 
	CONSTRAINT ck_refunds_erp_check_5 CHECK (amount > 0), 
	CONSTRAINT fk_refunds_receipt_id_payment_receipts FOREIGN KEY(receipt_id) REFERENCES payment_receipts (id), 
	CONSTRAINT fk_refunds_requested_by_users FOREIGN KEY(requested_by) REFERENCES users (id), 
	CONSTRAINT fk_refunds_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id), 
	CONSTRAINT fk_refunds_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_refunds_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_refunds_facility_id ON refunds (facility_id);

CREATE INDEX ix_refunds_organization_id ON refunds (organization_id);

CREATE INDEX ix_refunds_receipt_id ON refunds (receipt_id);


CREATE TABLE remittances (
	claim_id VARCHAR(64) NOT NULL, 
	source_key VARCHAR(160) NOT NULL, 
	approved_amount NUMERIC(18, 2) NOT NULL, 
	synthetic BOOLEAN NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_remittances PRIMARY KEY (id), 
	CONSTRAINT uq_remittances_organization_id_source_key UNIQUE (organization_id, source_key), 
	CONSTRAINT ck_remittances_erp_check_3 CHECK (approved_amount >= 0), 
	CONSTRAINT uq_remittances_claim_id UNIQUE (claim_id), 
	CONSTRAINT fk_remittances_claim_id_claims FOREIGN KEY(claim_id) REFERENCES claims (id), 
	CONSTRAINT fk_remittances_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_remittances_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_remittances_facility_id ON remittances (facility_id);

CREATE INDEX ix_remittances_organization_id ON remittances (organization_id);


CREATE TABLE report_acknowledgments (
	batch_id VARCHAR(64) NOT NULL, 
	source_type VARCHAR(40) NOT NULL, 
	reference TEXT NOT NULL, 
	recorded_by VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_report_acknowledgments PRIMARY KEY (id), 
	CONSTRAINT fk_report_acknowledgments_batch_id_report_batches FOREIGN KEY(batch_id) REFERENCES report_batches (id), 
	CONSTRAINT fk_report_acknowledgments_recorded_by_users FOREIGN KEY(recorded_by) REFERENCES users (id), 
	CONSTRAINT fk_report_acknowledgments_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_report_acknowledgments_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_report_acknowledgments_batch_id ON report_acknowledgments (batch_id);

CREATE INDEX ix_report_acknowledgments_facility_id ON report_acknowledgments (facility_id);

CREATE INDEX ix_report_acknowledgments_organization_id ON report_acknowledgments (organization_id);


CREATE TABLE report_batches (
	name VARCHAR(200) NOT NULL, 
	definition_version VARCHAR(100) NOT NULL, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	original_id VARCHAR(64), 
	summary JSONB, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_report_batches PRIMARY KEY (id), 
	CONSTRAINT fk_report_batches_original_id_report_batches FOREIGN KEY(original_id) REFERENCES report_batches (id), 
	CONSTRAINT fk_report_batches_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_report_batches_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_report_batches_facility_id ON report_batches (facility_id);

CREATE INDEX ix_report_batches_organization_id ON report_batches (organization_id);


CREATE TABLE report_lineage (
	id VARCHAR(64) NOT NULL, 
	batch_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	source_version INTEGER NOT NULL, 
	source_status VARCHAR(40) NOT NULL, 
	CONSTRAINT pk_report_lineage PRIMARY KEY (id), 
	CONSTRAINT uq_report_lineage_batch_id_encounter_id UNIQUE (batch_id, encounter_id), 
	CONSTRAINT fk_report_lineage_batch_id_report_batches FOREIGN KEY(batch_id) REFERENCES report_batches (id), 
	CONSTRAINT fk_report_lineage_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id)
)

;

CREATE INDEX ix_report_lineage_batch_id ON report_lineage (batch_id);


CREATE TABLE role_permissions (
	role_id VARCHAR(64) NOT NULL, 
	permission_id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id), 
	CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id), 
	CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id)
)

;


CREATE TABLE roles (
	id VARCHAR(64) NOT NULL, 
	label VARCHAR(120) NOT NULL, 
	CONSTRAINT pk_roles PRIMARY KEY (id)
)

;


CREATE TABLE rosters (
	staff_id VARCHAR(64) NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	original_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_rosters PRIMARY KEY (id), 
	CONSTRAINT ck_rosters_erp_check_11 CHECK (ends_at > starts_at), 
	CONSTRAINT fk_rosters_staff_id_staff_members FOREIGN KEY(staff_id) REFERENCES staff_members (id), 
	CONSTRAINT fk_rosters_original_id_rosters FOREIGN KEY(original_id) REFERENCES rosters (id), 
	CONSTRAINT fk_rosters_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_rosters_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_rosters_facility_id ON rosters (facility_id);

CREATE INDEX ix_rosters_organization_id ON rosters (organization_id);

CREATE INDEX ix_rosters_staff_id ON rosters (staff_id);


CREATE TABLE security_events (
	organization_id VARCHAR(64), 
	facility_id VARCHAR(64), 
	actor_id VARCHAR(64), 
	method VARCHAR(8) NOT NULL, 
	route_template VARCHAR(200) NOT NULL, 
	status_code INTEGER NOT NULL, 
	event VARCHAR(64) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_security_events PRIMARY KEY (id), 
	CONSTRAINT fk_security_events_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_security_events_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_security_events_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE seed_runs (
	version VARCHAR(64) NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_seed_runs PRIMARY KEY (version)
)

;


CREATE TABLE sessions (
	user_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	csrf_hash VARCHAR(64) NOT NULL, 
	csrf_token VARCHAR(100) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_sessions_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT uq_sessions_token_hash UNIQUE (token_hash)
)

;

CREATE INDEX ix_sessions_user_id ON sessions (user_id);


CREATE TABLE staff_members (
	user_id VARCHAR(64) NOT NULL, 
	department_id VARCHAR(64) NOT NULL, 
	credential_status VARCHAR(30) NOT NULL, 
	credential_valid_until DATE NOT NULL, 
	privilege VARCHAR(80) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_staff_members PRIMARY KEY (id), 
	CONSTRAINT uq_staff_members_user_id UNIQUE (user_id), 
	CONSTRAINT fk_staff_members_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_staff_members_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
	CONSTRAINT fk_staff_members_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_staff_members_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_staff_members_facility_id ON staff_members (facility_id);

CREATE INDEX ix_staff_members_organization_id ON staff_members (organization_id);


CREATE TABLE stock_balances (
	id VARCHAR(64) NOT NULL, 
	lot_id VARCHAR(64) NOT NULL, 
	location_id VARCHAR(64) NOT NULL, 
	available NUMERIC(18, 3) NOT NULL, 
	quarantined NUMERIC(18, 3) NOT NULL, 
	CONSTRAINT pk_stock_balances PRIMARY KEY (id), 
	CONSTRAINT uq_stock_balances_lot_id_location_id UNIQUE (lot_id, location_id), 
	CONSTRAINT ck_stock_balances_erp_check_9 CHECK (available >= 0 AND quarantined >= 0), 
	CONSTRAINT fk_stock_balances_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT fk_stock_balances_location_id_stock_locations FOREIGN KEY(location_id) REFERENCES stock_locations (id)
)

;


CREATE TABLE stock_counts (
	lot_id VARCHAR(64) NOT NULL, 
	location_id VARCHAR(64) NOT NULL, 
	observed_available NUMERIC(18, 3) NOT NULL, 
	counted_available NUMERIC(18, 3) NOT NULL, 
	reason TEXT NOT NULL, 
	counted_by VARCHAR(64) NOT NULL, 
	approved_by VARCHAR(64), 
	movement_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_stock_counts PRIMARY KEY (id), 
	CONSTRAINT ck_stock_counts_count_nonnegative CHECK (observed_available >= 0 AND counted_available >= 0), 
	CONSTRAINT fk_stock_counts_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT fk_stock_counts_location_id_stock_locations FOREIGN KEY(location_id) REFERENCES stock_locations (id), 
	CONSTRAINT fk_stock_counts_counted_by_users FOREIGN KEY(counted_by) REFERENCES users (id), 
	CONSTRAINT fk_stock_counts_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id), 
	CONSTRAINT fk_stock_counts_movement_id_stock_movements FOREIGN KEY(movement_id) REFERENCES stock_movements (id), 
	CONSTRAINT fk_stock_counts_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_stock_counts_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_stock_counts_facility_id ON stock_counts (facility_id);

CREATE INDEX ix_stock_counts_organization_id ON stock_counts (organization_id);


CREATE TABLE stock_locations (
	name VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_stock_locations PRIMARY KEY (id), 
	CONSTRAINT fk_stock_locations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_stock_locations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_stock_locations_facility_id ON stock_locations (facility_id);

CREATE INDEX ix_stock_locations_organization_id ON stock_locations (organization_id);


CREATE TABLE stock_movements (
	lot_id VARCHAR(64) NOT NULL, 
	location_id VARCHAR(64) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	source_id VARCHAR(200) NOT NULL, 
	operation_key VARCHAR(200) NOT NULL, 
	original_movement_id VARCHAR(64), 
	disposition VARCHAR(30) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_stock_movements PRIMARY KEY (id), 
	CONSTRAINT uq_stock_movements_organization_id_operation_key UNIQUE (organization_id, operation_key), 
	CONSTRAINT ck_stock_movements_erp_check_10 CHECK (quantity <> 0), 
	CONSTRAINT fk_stock_movements_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT fk_stock_movements_location_id_stock_locations FOREIGN KEY(location_id) REFERENCES stock_locations (id), 
	CONSTRAINT fk_stock_movements_original_movement_id_stock_movements FOREIGN KEY(original_movement_id) REFERENCES stock_movements (id), 
	CONSTRAINT fk_stock_movements_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_stock_movements_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_stock_movements_facility_id ON stock_movements (facility_id);

CREATE INDEX ix_stock_movements_organization_id ON stock_movements (organization_id);


CREATE TABLE stock_reservations (
	task_id VARCHAR(64) NOT NULL, 
	lot_id VARCHAR(64) NOT NULL, 
	location_id VARCHAR(64) NOT NULL, 
	quantity NUMERIC(18, 3) NOT NULL, 
	movement_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_stock_reservations PRIMARY KEY (id), 
	CONSTRAINT ck_stock_reservations_reservation_positive CHECK (quantity > 0), 
	CONSTRAINT fk_stock_reservations_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_stock_reservations_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES inventory_lots (id), 
	CONSTRAINT fk_stock_reservations_location_id_stock_locations FOREIGN KEY(location_id) REFERENCES stock_locations (id), 
	CONSTRAINT fk_stock_reservations_movement_id_stock_movements FOREIGN KEY(movement_id) REFERENCES stock_movements (id), 
	CONSTRAINT fk_stock_reservations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_stock_reservations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_stock_reservations_facility_id ON stock_reservations (facility_id);

CREATE INDEX ix_stock_reservations_organization_id ON stock_reservations (organization_id);

CREATE INDEX ix_stock_reservations_task_id ON stock_reservations (task_id);


CREATE TABLE supplier_obligations (
	purchase_id VARCHAR(64) NOT NULL, 
	supplier_id VARCHAR(64) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_supplier_obligations PRIMARY KEY (id), 
	CONSTRAINT uq_supplier_obligations_purchase_id UNIQUE (purchase_id), 
	CONSTRAINT fk_supplier_obligations_purchase_id_purchases FOREIGN KEY(purchase_id) REFERENCES purchases (id), 
	CONSTRAINT fk_supplier_obligations_supplier_id_suppliers FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	CONSTRAINT fk_supplier_obligations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_supplier_obligations_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_supplier_obligations_facility_id ON supplier_obligations (facility_id);

CREATE INDEX ix_supplier_obligations_organization_id ON supplier_obligations (organization_id);


CREATE TABLE suppliers (
	name VARCHAR(200) NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_suppliers PRIMARY KEY (id), 
	CONSTRAINT fk_suppliers_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_suppliers_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id)
)

;

CREATE INDEX ix_suppliers_facility_id ON suppliers (facility_id);

CREATE INDEX ix_suppliers_organization_id ON suppliers (organization_id);


CREATE TABLE task_coordination (
	task_id VARCHAR(64) NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE, 
	priority VARCHAR(12) DEFAULT 'normal' NOT NULL, 
	escalation_level INTEGER DEFAULT '0' NOT NULL, 
	escalation_reason VARCHAR(2000), 
	escalated_at TIMESTAMP WITH TIME ZONE, 
	operational_updates INTEGER DEFAULT '0' NOT NULL, 
	CONSTRAINT pk_task_coordination PRIMARY KEY (task_id), 
	CONSTRAINT ck_task_coordination_operational_priority CHECK (priority IN ('low','normal','high')), 
	CONSTRAINT ck_task_coordination_operational_bounds CHECK (escalation_level BETWEEN 0 AND 3 AND operational_updates >= 0), 
	CONSTRAINT fk_task_coordination_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id)
)

;

CREATE INDEX ix_task_coordination_due_at ON task_coordination (due_at);


CREATE TABLE tasks (
	organization_id VARCHAR(64) NOT NULL, 
	facility_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	encounter_id VARCHAR(64) NOT NULL, 
	domain VARCHAR(8) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	title VARCHAR(240) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	version INTEGER NOT NULL, 
	assignee_id VARCHAR(64), 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_tasks PRIMARY KEY (id), 
	CONSTRAINT fk_tasks_encounter_id_patient_id_organization_id_facili_131c FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), 
	CONSTRAINT fk_tasks_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_tasks_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), 
	CONSTRAINT fk_tasks_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), 
	CONSTRAINT fk_tasks_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), 
	CONSTRAINT fk_tasks_assignee_id_users FOREIGN KEY(assignee_id) REFERENCES users (id)
)

;

CREATE INDEX ix_tasks_encounter_id ON tasks (encounter_id);

CREATE INDEX ix_tasks_facility_id ON tasks (facility_id);

CREATE INDEX ix_tasks_organization_id ON tasks (organization_id);

CREATE INDEX ix_tasks_patient_id ON tasks (patient_id);


CREATE TABLE user_patient_scopes (
	user_id VARCHAR(64) NOT NULL, 
	patient_id VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_user_patient_scopes PRIMARY KEY (user_id, patient_id), 
	CONSTRAINT fk_user_patient_scopes_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_user_patient_scopes_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id)
)

;


CREATE TABLE users (
	organization_id VARCHAR(64) NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	display_name VARCHAR(200) NOT NULL, 
	password_hash TEXT NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	version INTEGER NOT NULL, 
	id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT fk_users_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT uq_users_username UNIQUE (username)
)

;

CREATE INDEX ix_users_organization_id ON users (organization_id);
