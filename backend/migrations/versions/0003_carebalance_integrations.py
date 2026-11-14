# Durable CareBalance connector bindings and transport evidence.
from alembic import op

revision = '0003_carebalance_integrations'
down_revision = '0002_live_inference'
branch_labels = None
depends_on = None

# Frozen PostgreSQL schema; runtime models are not imported by migration.
DDL = ("\nCREATE TABLE connector_bindings (\n\tconnector VARCHAR(24) NOT NULL, \n\torganization_id VARCHAR(64) NOT NULL, \n\tfacility_id VARCHAR(64) NOT NULL, \n\tactor_id VARCHAR(64) NOT NULL, \n\tsession_id VARCHAR(64) NOT NULL, \n\tpatient_id VARCHAR(64) NOT NULL, \n\tencounter_id VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64) NOT NULL, \n\tsource_id VARCHAR(64) NOT NULL, \n\tsource_version INTEGER NOT NULL, \n\tsource_hash VARCHAR(64) NOT NULL, \n\tsource_snapshot JSONB NOT NULL, \n\tlab_values JSONB NOT NULL, \n\texternal_report_id VARCHAR(128), \n\tstate VARCHAR(24) NOT NULL, \n\tid VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_connector_bindings PRIMARY KEY (id), \n\tCONSTRAINT uq_connector_binding_source UNIQUE (actor_id, session_id, connector, task_id, source_id, source_version), \n\tCONSTRAINT fk_connector_binding_encounter_scope FOREIGN KEY(encounter_id, patient_id, organization_id, facility_id) REFERENCES encounters (id, patient_id, organization_id, facility_id), \n\tCONSTRAINT ck_connector_bindings_positive_source_version CHECK (source_version > 0), \n\tCONSTRAINT ck_connector_bindings_known_connector CHECK (connector = 'labclear'), \n\tCONSTRAINT ck_connector_bindings_binding_state CHECK (state IN ('reserved','draft','confirmed','unknown','quarantined')), \n\tCONSTRAINT fk_connector_bindings_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tCONSTRAINT fk_connector_bindings_facility_id_facilities FOREIGN KEY(facility_id) REFERENCES facilities (id), \n\tCONSTRAINT fk_connector_bindings_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), \n\tCONSTRAINT fk_connector_bindings_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), \n\tCONSTRAINT fk_connector_bindings_patient_id_patients FOREIGN KEY(patient_id) REFERENCES patients (id), \n\tCONSTRAINT fk_connector_bindings_encounter_id_encounters FOREIGN KEY(encounter_id) REFERENCES encounters (id), \n\tCONSTRAINT fk_connector_bindings_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), \n\tCONSTRAINT fk_connector_bindings_source_id_clinical_labs FOREIGN KEY(source_id) REFERENCES clinical_labs (id)\n)\n\n", "\nCREATE TABLE connector_attempts (\n\tbinding_id VARCHAR(64) NOT NULL, \n\tactor_id VARCHAR(64) NOT NULL, \n\tsession_id VARCHAR(64) NOT NULL, \n\toperation VARCHAR(24) NOT NULL, \n\toperation_key VARCHAR(120) NOT NULL, \n\trequest_id VARCHAR(64) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tauthorization_hash VARCHAR(64) NOT NULL, \n\tpayload JSONB NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tlease_id VARCHAR(64) NOT NULL, \n\tlease_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tresponse JSONB, \n\terror_code VARCHAR(64), \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tid VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_connector_attempts PRIMARY KEY (id), \n\tCONSTRAINT uq_connector_attempt_actor_session_key UNIQUE (actor_id, session_id, operation_key), \n\tCONSTRAINT ck_connector_attempts_attempt_operation CHECK (operation IN ('import','read','confirm')), \n\tCONSTRAINT ck_connector_attempts_attempt_status CHECK (status IN ('running','succeeded','unknown','rejected','quarantined')), \n\tCONSTRAINT fk_connector_attempts_binding_id_connector_bindings FOREIGN KEY(binding_id) REFERENCES connector_bindings (id), \n\tCONSTRAINT fk_connector_attempts_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id), \n\tCONSTRAINT fk_connector_attempts_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id), \n\tCONSTRAINT uq_connector_attempts_request_id UNIQUE (request_id)\n)\n\n", "\nCREATE TABLE connector_exchanges (\n\tattempt_id VARCHAR(64) NOT NULL, \n\tcontext_snapshot JSONB NOT NULL, \n\toutcome VARCHAR(24) NOT NULL, \n\treceipt JSONB, \n\terror_code VARCHAR(64), \n\tquarantined BOOLEAN NOT NULL, \n\tquarantine_reason VARCHAR(64), \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tid VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_connector_exchanges PRIMARY KEY (id), \n\tCONSTRAINT ck_connector_exchanges_exchange_outcome CHECK (outcome IN ('running','succeeded','unknown','rejected')), \n\tCONSTRAINT fk_connector_exchanges_attempt_id_connector_attempts FOREIGN KEY(attempt_id) REFERENCES connector_attempts (id)\n)\n\n", 'CREATE INDEX ix_connector_attempts_binding_id ON connector_attempts (binding_id)', 'CREATE INDEX ix_connector_exchanges_attempt_id ON connector_exchanges (attempt_id)')


def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.execute("""CREATE FUNCTION his_guard_connector_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'connector evidence cannot be deleted'; END IF;
      IF TG_TABLE_NAME = 'connector_bindings' THEN
        IF (to_jsonb(NEW) - ARRAY['state','external_report_id']) IS DISTINCT FROM
           (to_jsonb(OLD) - ARRAY['state','external_report_id']) THEN
          RAISE EXCEPTION 'connector binding source is immutable';
        END IF;
        IF OLD.external_report_id IS NOT NULL AND NEW.external_report_id IS DISTINCT FROM OLD.external_report_id THEN
          RAISE EXCEPTION 'connector external report identity is immutable';
        END IF;
      ELSIF TG_TABLE_NAME = 'connector_attempts' THEN
        IF (to_jsonb(NEW) - ARRAY['status','lease_id','lease_expires_at','response','error_code','completed_at']) IS DISTINCT FROM
           (to_jsonb(OLD) - ARRAY['status','lease_id','lease_expires_at','response','error_code','completed_at']) THEN
          RAISE EXCEPTION 'connector request identity is immutable';
        END IF;
        IF OLD.status = 'succeeded' AND NEW IS DISTINCT FROM OLD THEN
          RAISE EXCEPTION 'completed connector attempt is immutable';
        END IF;
      ELSE
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.attempt_id IS DISTINCT FROM OLD.attempt_id OR
           NEW.context_snapshot IS DISTINCT FROM OLD.context_snapshot OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
          RAISE EXCEPTION 'connector exchange identity is immutable';
        END IF;
        IF OLD.outcome <> 'running' AND
           (to_jsonb(NEW) - ARRAY['quarantined','quarantine_reason']) IS DISTINCT FROM
           (to_jsonb(OLD) - ARRAY['quarantined','quarantine_reason']) THEN
          RAISE EXCEPTION 'completed connector exchange receipt is immutable';
        END IF;
      END IF;
      RETURN NEW;
    END $$""")
    for table in ["connector_bindings", "connector_attempts", "connector_exchanges"]:
        op.execute(f"CREATE TRIGGER {table}_guard BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION his_guard_connector_evidence()")


def downgrade():
    raise RuntimeError('Connector source and outcome evidence require a reviewed archival migration')
