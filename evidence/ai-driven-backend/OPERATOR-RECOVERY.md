# Private recovery of remote UNKNOWN

There is no public clear API or automatic timeout release. This guide documents
the private function prepared for the integrator; it was not executed against a
server or production database by the backend worker.

1. Quiesce **every HIS generation path**, including the assistant worker and
   legacy document-review dispatch. Keep queued jobs from starting. Preserve
   affected run IDs, original errors, provider reasons, lease identities and logs.
2. Independently establish that the pinned provider's affected work has completed
   or was cancelled/drained. Retain completion/cancellation and host/provider
   evidence. A TTL or empty `/api/ps` response alone is insufficient. Any host or
   container action must stay within the separately authorized HIS resources.
3. Use an active persisted operator Actor with `identity.admin` and `D38.write`
   in the same organization/facility as the affected attempt. The private function
   revalidates this session and current permissions. It rejects active unexpired
   runs that have not yet become quarantined.
4. In the trusted operator process, within one database transaction, call:

```python
from backend.app.assistant_reconciliation import (
    ACKNOWLEDGEMENT, reconcile_unknown_inference,
)

# db is an explicit SessionLocal.begin() transaction on the intended database.
# operator is the existing verified, active admin Actor; no credential is logged.
marker = reconcile_unknown_inference(
    db, operator,
    kind="assistant",  # or "legacy"
    run_id=affected_run_id,
    acknowledgement=ACKNOWLEDGEMENT,
    evidence_reference=retained_completion_or_cancellation_receipt,
    workers_quiesced=True,
    provider_drained=True,
)
```

The exact acknowledgement is:

> I confirm HIS workers are quiesced and the pinned provider is drained

5. Commit, then verify the returned marker's audit event and the run's read-only
   admission status. The marker is bound to the exact attempt identity and an
   audit-event hash; arbitrary provider/provenance JSON cannot clear UNKNOWN.
   Original errors/results remain. An expired running row becomes interrupted;
   its clinical review does not become valid.
6. Check host/provider resources again before separately resuming dispatch.
   Reconciliation releases admission only. It does not requeue, retry, approve,
   attest, sign, release a result or apply an old clinical artifact.

Trusted adapter dispatch telemetry can also produce audited
`positive_terminal_evidence`: the adapter observed the pinned model, `done=true`
and a canonical response SHA. This physical proof may clear admission even when
the clinical artifact or a later identity check fails. Clinical rejection and
source/review staleness remain unchanged. Audited `no_dispatch_evidence` proves a
failure occurred before chat dispatch. Raw flags and generic outcome labels do
not establish either proof; dispatched failures without terminal evidence remain
UNKNOWN regardless of TTL. Flagless older adapters retain conservative legacy
reason handling. All markers remain read-only through the API.
