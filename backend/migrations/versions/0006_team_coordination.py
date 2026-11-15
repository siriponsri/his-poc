"""Add typed task coordination without rewriting any existing row."""
from alembic import op

revision = '0006_team_coordination'
down_revision = '0005_assistant_workspaces'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE task_coordination (
        task_id VARCHAR(64) PRIMARY KEY REFERENCES tasks(id),
        due_at TIMESTAMP WITH TIME ZONE,
        priority VARCHAR(12) DEFAULT 'normal' NOT NULL,
        escalation_level INTEGER DEFAULT 0 NOT NULL,
        escalation_reason VARCHAR(2000),
        escalated_at TIMESTAMP WITH TIME ZONE,
        operational_updates INTEGER DEFAULT 0 NOT NULL,
        CONSTRAINT ck_task_coordination_operational_priority
            CHECK (priority IN ('low','normal','high')),
        CONSTRAINT ck_task_coordination_operational_bounds
            CHECK (escalation_level BETWEEN 0 AND 3 AND operational_updates >= 0)
    )""")
    op.execute('CREATE INDEX ix_task_coordination_due_at ON task_coordination(due_at)')


def downgrade():
    raise RuntimeError('No destructive downgrade; preserve current coordination and use a schema-compatible application rollback')
