"""One PostgreSQL admission fence shared by legacy and assistant inference."""
import hashlib
from datetime import timedelta
from sqlalchemy import select, text, or_
from .models import InferenceRun
from .models_assistant import AssistantRun
from .common import utcnow

def admission_busy(db, *, legacy_id=None, assistant_id=None, now=None):
    now=now or utcnow()
    key=int.from_bytes(hashlib.sha256(b'his-inference-admission:global:v1').digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':key})
    legacy=db.scalars(select(InferenceRun).where(InferenceRun.id!=legacy_id if legacy_id else text('true'), InferenceRun.provider!='mock_demo', or_(InferenceRun.outcome.in_(['running','timeout','interrupted']),InferenceRun.provenance['provider_outcome'].astext=='timeout')))
    for run in legacy:
        hold=run.created_at+timedelta(seconds=int((run.context_snapshot or {}).get('lease_seconds',360)))
        if hold>now:
            return True
    rows=db.scalars(select(AssistantRun).where(AssistantRun.id!=assistant_id if assistant_id else text('true'),or_(AssistantRun.execution_state=='running',AssistantRun.hold_until>now)))
    for run in rows:
        if (run.hold_until and run.hold_until>now) or (run.lease_expires_at and run.lease_expires_at>now):
            return True
    return False
