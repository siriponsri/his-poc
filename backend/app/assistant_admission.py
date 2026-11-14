"""One PostgreSQL admission fence shared by legacy and assistant inference."""
import hashlib
from sqlalchemy import select, text
from .models import InferenceRun
from .models_assistant import AssistantRun
from .common import utcnow
from .assistant_reconciliation import admission_status

def lock_admission(db):
    key=int.from_bytes(hashlib.sha256(b'his-inference-admission:global:v1').digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':key})

def admission_busy(db, *, legacy_id=None, assistant_id=None, now=None):
    lock_admission(db)
    # A production caller may wait for this lock; age leases only after acquiring it.
    now=now if now is not None else utcnow()
    legacy=db.scalars(select(InferenceRun).where(InferenceRun.id!=legacy_id if legacy_id else text('true'), InferenceRun.provider!='mock_demo'))
    for run in legacy:
        if admission_status(db,run,'legacy',now)['state']!='clear':return True
    rows=db.scalars(select(AssistantRun).where(AssistantRun.id!=assistant_id if assistant_id else text('true')))
    for run in rows:
        if admission_status(db,run,'assistant',now)['state']!='clear':return True
    return False
