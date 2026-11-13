"""Initial relational PostgreSQL full-system development schema.

Revision ID: 0001_fullsystem
Schema snapshot is frozen in schema_0001.py; later changes require new revisions.
"""
from alembic import op
from backend.migrations.schema_0001 import DDL
revision='0001_fullsystem'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    for statement in DDL: op.execute(statement)
    op.execute("""CREATE FUNCTION his_deny_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable evidence or posted result'; END $$""")
    for table in ['document_versions','document_attestations','proposal_versions','human_reviews','committed_results','audit_events','operations','security_events','clinical_events','clinical_medication_returns','clinical_therapy_sessions','clinical_therapy_progress','clinical_immunizations','clinical_handover_tasks']:
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION his_deny_immutable_change()')
    from backend.migrations.erp_guards import DDL as erp_guards
    for statement in erp_guards:op.execute(statement)
def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore verified isolated backup or write reviewed forward migration')
