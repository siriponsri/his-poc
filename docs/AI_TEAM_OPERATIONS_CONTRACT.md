# AI evidence, accountable work and administration operations

Status: ACTIVE_IMPLEMENTATION. Owner authorization: 15 November 2026, this chat.
Base: c47868a. This extends the retained v1 assistant and Admin contracts.

## Delivery and authority

Implement all three features, qualify against disposable PostgreSQL 18, deploy
the named synthetic POC on dr-train and test through his.ai-cie.com. Publication
to the existing main remote remains authorized. No paid API, model installation,
training, real patient data, external notification or unrelated service change.
Root integrates and owns shared schema/identity/contracts and the final release.
Workers have separate existing checkouts with non-overlapping files. Independent
review precedes the operational transition. No automatic retry of uncertain work.

Use the existing pinned private Typhoon service, 4096 context, 512 output tokens,
2000 UTF-8 byte inference view, 12 included sources and one inference admission.
New synthetic application acceptance allowance: at most EIGHT generations total,
including at most TWO corrective reserves, across four existing profiles. No
automatic batch/watch trial, direct-generation qualification, cloud fallback or
retry of the same failed source. Record every attempt, latency, usage and outcome;
unmeasured money remains null. Stop new calls when the allowance is exhausted.
This new owner-authorized acceptance is separate from the exhausted older trial.
Local checks are bounded per suite; use targeted tests before broader integration.

## A. Source quality and evidence

Select relevant permitted content before identity boilerplate. Retain complete
authoritative manifests and use exact bounded passages for long notes instead of
discarding every long note. Each excerpt retains its original Unicode code-point
start/end and revision/hash; disclose partial selection and complete omissions.
Do not interpret urgency, invent thresholds or select inaccessible sources.
Records stays metadata-only; nursing gains no laboratory access. Exclude pristine
assistant output and preserve all old run/revision/result bytes.

No prompt/schema/model/context enlargement is planned. Strict exact quote/typed
field validation remains authoritative. Quality is a deterministic evidence and
coverage report, never self-reported confidence or clinical correctness. Generated
prose still requires human review; a citation alone does not certify its meaning.
An explicit new prepare may use an improved input selection; passive page loads
and ownership-only edits must not dispatch generation.

RunDTO additions:

- `quality`: `{selection_version, included_by_kind, eligible_by_kind,
  omitted_by_kind, partial_source_count, verified_fact_count,
  draft_attribution:"source_references_only_requires_human_review"}`.
- `sources[]` retains existing fields and adds `identity`, `version`,
  `revision_id`, `content_hash`, `selection` (`whole` or `excerpt`),
  `excerpt_start`, `excerpt_end`, `offset_unit:"unicode_code_points"`,
  `evidence_url`. Legacy packets report absent selection metadata explicitly.
- `omitted_sources[]`: authorized `{kind,label,reason}` without body text.
- `GET /assistant/runs/{id}/sources/{ref}` returns the immutable permitted
  snapshot `{ref,kind,label,identity,version,revision_id,content_hash,fields,
  text,selection,excerpt_start,excerpt_end,offset_unit,source_freshness}`.
  Revalidate existing actor-owned run, current permissions/care scope and
  authorization hash. It does not fetch another actor's artifact or invoke AI.

Exact cited passages can be highlighted in the snapshot. Display stale originals
as dated snapshots; mutation/apply still checks latest source/revision/hash and
the existing immutable human edit/decision/idempotency protocol.

## B. Accountable team queue

Reuse Task.assignee_id and Task.version. Add one typed `task_coordination` table
(migration 0006_team_coordination) keyed by task_id: due_at nullable timezone-aware,
priority low/normal/high, escalation_level 0..3, escalation_reason nullable,
escalated_at nullable, operational_updates >=0. No duplicate task identity/auth.
No startup seed/reset; explicitly qualify and migrate with preservation/rollback.

Every coordination mutation increments Task.version and operational_updates in
one transaction. Source semantic version is Task.version-operational_updates;
claim/schedule/escalation alone does not expose pristine assistant text or change
the assistant source digest. Genuine domain status/content changes remain sources.

Router `/team-queue` (all paths below under /api/v2):

- `GET /team-queue`: q max100, domain optional, view all/mine/unassigned,
  status active/open/in_progress/completed/cancelled/all, offset>=0, limit1..50.
  Response `{items,total,offset,limit,scope:"authorized_work",observed_at,
  counts:{active,mine,unassigned,overdue,escalated},counts_scope:"authorized_active_work"}`.
  Counts use current q/domain and authorized active tasks before view/status.
- Each item: existing task fields plus `patient_label`,
  `assignee:{id,display_name,username}|null`, `due_at`, `priority`,
  `escalation_level`, `escalation_reason`, `escalated_at`, `overdue`,
  `capabilities:{claim,release,assign,schedule,escalate}`.
- `GET /team-queue/tasks/{id}` gives that exact item.
- `GET /team-queue/tasks/{id}/assignees` gives `{items:[{id,display_name,username}]}`.
- POST `/tasks/{id}/claim` or `/release`: `{version}`.
- POST `/tasks/{id}/assign`: `{version,assignee_id,reason}`.
- POST `/tasks/{id}/schedule`: `{version,due_at,priority}`.
- POST `/tasks/{id}/escalate`: `{version,reason}`.
  Each returns the updated item directly, requires CSRF/Idempotency-Key,
  current scope and domain.write, row lock and expected Task.version, and stores
  Task/coordination/audit/idempotent result atomically. Replays revalidate current
  authorization and context. Exactly one concurrent claim wins. Terminal tasks
  reject coordination; existing order/review completion guards remain unchanged.

Claim only unassigned/self (another owner conflicts). Release only self.
Reassignment requires a nonempty handoff reason and a currently active same-org,
same-facility nonportal colleague with persisted domain read/write, credential
eligibility and current patient/care scope. Directory shows only eligible people.
Escalate only overdue active work, at most level3; keep the same task/owner and
append audit. Priority and due dates are operational, never medical triage.
No email/SMS, automatic completion, duplicate obligation or authority transfer.
Reassignment does not share an actor-owned AI run.

## C. Admin AI monitoring

`GET /admin/ai-operations`: profile optional, state optional, offset>=0, limit1..50.
Require persisted D34.read and identity.admin in current org/facility. Read-only:
no provider probe/generation, patient/chart collector, retry/cancel or platform
control. Select only permitted scalar operational columns and aggregate JSON
counts; never SELECT full inference_view/source_manifest/artifact bodies.

Response `{observed_at,scope,provider,worker,counts,profiles,items,total,offset,limit}`.
`provider` is declared configuration with `live_status:"not_checked"` and
`declared_qualified_profiles`; it is not a new runtime/model qualification.
`worker` distinguishes unknown heartbeat from dated persisted start/completion.
`counts` covers all execution states and pending human review in this facility;
`profiles` has per-profile state counts. Item fields: id,profile,execution_state,
review_state,error,created_at,started_at,completed_at,elapsed_ms,usage,
measured_cost,coverage,revision_count,effect_count,
`evidence_freshness:"not_checked_for_admin"`. No patient/encounter labels/IDs,
source text, model output, raw provider payload, credential or session identifier.
Costs are null when unmeasured, and latest success is historical activity rather
than a heartbeat or claim that every profile is currently clinically qualified.

## Acceptance

Meaningful PostgreSQL tests: scoped pagination, eligibility/revocation, concurrent
claim, stale versions/idempotent replay, one overdue escalation, domain completion
guards, ownership-only source stability, metadata-only collector SQL, exact
snapshot citations, stale/apply fences and Admin no-body/no-generation reads.
Compare synthetic long/multi-source selection fixtures with the retained policy:
show substantive note/lab/task evidence and omissions, not just title/DOB facts.
Test the four unchanged provider schemas with actual bounded application calls.

Mounted UI tests plus typecheck/build cover filtering, owner/due/escalation forms,
source/snapshot highlighting, nonblocking processing and Admin monitoring states.
Protected browser journeys exercise AI evidence, accountable task mutation/reload,
and Admin monitoring without clinical signing. Report exact subset and results;
do not claim a new all38/all10 run, clinical effectiveness or saved staff minutes.
Update architecture/config/contracts/goal/plan/backlog/guide and release evidence.
