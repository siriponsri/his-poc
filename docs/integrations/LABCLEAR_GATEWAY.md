# HIS LabClear gateway contract

Backend-only implementation checkpoint. No production environment, migration,
seed, receiver service or public URL is changed by this source work.

All routes use the current HIS cookie session. POST requires `X-CSRF-Token`.
Every route revalidates the active account/session/membership/credential and D10
write permission, plus current patient/encounter assignment. A binding belongs to
one actor and originating session; it cannot be transferred by passing an ID.

| Route below `/api/v2/integrations/labclear` | Input |
|---|---|
| `POST /import` | `{patient_id, encounter_id, task_id, source_id, source_version}` plus `Idempotency-Key` |
| `GET /bindings?patient_id=...&encounter_id=...` | Both scope IDs required |
| `POST /bindings/{id}/read` | No body required; fresh server context, no upstream URL |
| `POST /bindings/{id}/recover` | No body required; return the owned pending command for explicit resumption, no receiver call |
| `POST /bindings/{id}/confirm` | `{fields:[{source_index,name,value,unit,reference,printed_flag}],same_person_confirmed:true,source_version,source_sha256}` plus `Idempotency-Key` |

The review task is a separately created D10 `labclear_review` task for the exact
same organization, facility, patient and encounter. Import/confirm require it to
be open/in_progress and the encounter to be active. Reads may review a completed
task or closed encounter, but still require current authorization and an unchanged
released/corrected source. Original order tasks are not reused or completed: the
existing laboratory release already completes its own order task.

The selected `clinical_labs` record must be released/corrected at the requested
version, with a correctly scoped linked clinical order. Exact analyte/result/unit/
reference strings come from PostgreSQL, never the browser. The source hash is the
canonical SHA-256 of the server-owned snapshot, stored in the binding with the
exact values. LabClear's narrower 100/150 analyte/value limits reject unsupported
sources without truncation. Confirmation indices must cover every source row in
original order. A changed source requires a new explicit binding/review.

## Response

Successful mutations/read return:

```json
{
  "binding": {
    "id": "opaque HIS binding ID", "connector": "labclear",
    "patient_id": "...", "encounter_id": "...", "task_id": "...",
    "source_id": "...", "source_version": 1, "source_sha256": "...",
    "external_report_id": "cb_report_...", "state": "draft or confirmed",
    "created_at": "UTC timestamp"
  },
  "attempt_id": "opaque durable attempt ID",
  "outcome": "succeeded",
  "receipt": {"report_id": "...", "state": "draft", "fields": [], "review": null}
}
```

`receipt` is the source-bound receipt validated by the frozen LabClear client; it
also includes protocol, source reference and transferred snapshot hash. It is not
a HIS signed/released result. The list returns `{connector:"labclear",available,
items:[binding...]}`; availability reflects explicit connector configuration.

Pending/unknown calls return HTTP 202 with the same envelope, `receipt:null`,
`outcome:"running"` or `"unknown"`. Mutations have `retry_same_key:true`: the browser must
retain the original idempotency key and payload. Retrying a mutation uses the same receiver
request ID and binding with fresh authentication/expiry/nonce. It does not create
another upstream report. A live lease returns pending without a duplicate call.
Changed payload with an existing key returns 409. A known receiver rejection
returns a generic gateway error without forwarding upstream text or credentials.

After a page refresh, `/recover` revalidates the current actor/session, active
task, unchanged released source and authorization snapshot before returning the
latest unresolved import/confirm command. The response is
`{binding,pending:null|{attempt_id,kind,path,method:"POST",key,body,lease_expires_at},retry_allowed}`.
Paths and methods are server-owned and stored bodies are revalidated against the
strict import/confirm DTO. No arbitrary stored URL or JSON command is returned.
The frontend explicitly resumes that exact body/key; recovery never resends it.
A live lease sets `retry_allowed:false`. Closed tasks, stale sources, removed
assignments or different actors/sessions cannot recover the command or its cells.
While a binding has an unresolved import/confirm attempt, a different mutation
key is rejected with `409 CONNECTOR_PENDING_RECOVERY_REQUIRED` and its opaque
binding ID. Only the exact original command/key may resume. Read and recovery
remain available; neither silently substitutes another confirmation payload.
Read attempts do not mutate the receiver and return `retry_same_key:false` when
their outcome is unknown; the user may make a fresh authorized read.
Reads have `retry_same_key:false`; repeating the read obtains fresh authorization
and a new server-side attempt without performing a receiver mutation.

## Transactions and race handling

Reserve immutable source/binding and a durable attempt/exchange under PostgreSQL
locks, commit and close the transaction, then call the receiver. No transaction is
held during HTTP. Each exchange retains the actual upstream outcome. Finalization
rechecks current session/permissions, exact binding, source and task. If anything
changed, preserve the upstream receipt as quarantined internal evidence and return
only the authorization/context denial, never its patient values. A late response
cannot overwrite a newer lease's result. No automatic worker replays an attempt.
Untrusted task/source IDs are filtered to the exact organization, facility,
patient and encounter before row locks are taken, so foreign row IDs cannot be
used to wait on another patient's work.

No action completes a task, releases/corrects a HIS lab result, signs a document,
calls OCR/AI, creates a referral or shares application cookies. Existing LabClear
Render/runtime and privacy-sharing gates remain outside this checkpoint.
