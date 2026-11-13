"""Durable external inference reservations; preserve all existing mock evidence.

Revision ID: 0002_live_inference
Revises: 0001_fullsystem
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision='0002_live_inference'
down_revision='0001_fullsystem'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('inference_runs',sa.Column('operation_key',sa.String(120),nullable=True))
    op.add_column('inference_runs',sa.Column('request_hash',sa.String(64),nullable=True))
    op.add_column('inference_runs',sa.Column('authorization_hash',sa.String(64),nullable=True))
    op.add_column('inference_runs',sa.Column('context_snapshot',postgresql.JSONB(),nullable=True))
    op.add_column('inference_runs',sa.Column('provenance',postgresql.JSONB(),nullable=True))
    op.add_column('inference_runs',sa.Column('completed_at',sa.DateTime(timezone=True),nullable=True))
    op.create_unique_constraint('uq_inference_runs_actor_id_operation_key','inference_runs',['actor_id','operation_key'])


def downgrade():
    # Inference provenance is historical evidence and cannot be discarded silently.
    raise RuntimeError('Live inference history requires an explicit archival migration; downgrade is disabled')
