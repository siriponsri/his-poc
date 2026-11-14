# CareBalance application integration contract

Status: LabClear implemented and privately qualified; DR receiver contract frozen
and implementation ACTIVE. Public connector acceptance is separate. Detailed
current evidence is in [the validation checkpoint](VALIDATION_CHECKPOINT_20261114.md).

## Authorized outcome

An authorized HIS user opens a specialist workspace from the selected patient,
visit and task. DR uses an independent CareBalance derivative; the original
DR repository and runtime are not an integration destination. LabClear keeps
its existing review journey and receives the CareBalance visual adapter.
HIS remains the authority for its patient, encounter and task. A specialist
application remains the authority for its report and human review history.

The owner authorized the three named repositories, a separate DR derivative,
LabClear source changes, and the existing dedicated HIS deployment. This does
not authorize modifying LabClear's current Render deployment, sending real
patient images, paid inference, training, or altering the original DR service.

## Observed need and alternatives

1. Keep separate links and manual context entry. This needs little code, but
   permits wrong-patient transcription and cannot bind a returned report to
   the originating source revision. Retain it only as an explicitly labelled
   fallback when a connector is unavailable.
2. Share cookies, embed an unscoped application, or trust patient IDs in a URL.
   This conflicts with independent authorization, LabClear's frame policy,
   and DR's workspace-wide reads. Rejected.
3. Use an explicit server integration protocol with isolated receiver state,
   opaque short-lived launch handles and immutable source/report references.
   Selected. Each application preserves its own clinical workflow and rejects
   mismatched identities, stale sources and replayed launches.

## Protocol boundaries

The browser talks to HIS with its existing session and CSRF protection. HIS
rechecks current account, membership, facility, patient, encounter and domain
permissions before creating a launch or reading a returned result. A launch
is not an authorization grant for unrestricted specialist API access.

HIS stores a binding containing organization, facility, patient, encounter,
actor, originating task, connector, external workspace/case or report ID,
source type/ID/version/hash, and an explicit purpose. Only opaque IDs may
appear in a launch URL. No patient names, passwords, service keys or source
bytes may appear there. Launch secrets are stored hashed, short lived,
single use, audience bound and bound to the originating HIS session.

Receiver exchange uses a separately provisioned service identity, authenticated
requests, bounded timestamps and nonce replay protection. The receiver must
obtain a freshly authorized context, then bind all reads and writes to that
context. It must never accept browser-supplied identity headers. An existing
application administrator is not impersonated. Session revocation, changed
membership and removed patient assignment invalidate subsequent access.

Both sender and receiver adapters must call `validate_context_lifetime` before
an operation, enforcing the expected audience and `now < expires_at <= now +
120 seconds`. The UTC wire timestamp uses an explicit `Z` suffix. Envelope
freshness is a separate maximum30-second clock-skew check. Consumed nonces
must remain stored through `max(now, timestamp) + max_skew_seconds` inclusive;
the initial receiver keeps them permanently. A new nonce is required for an
idempotent retry, while the semantic request ID and payload remain unchanged.

A receiver lacking these checks remains unavailable in the HIS UI. A health
response or completed launch exchange alone does not establish authorization
or clinical acceptance. All connector endpoints are disabled by default until
their configuration and receiver are validated.

## Source and result data contract

Every message includes a protocol version, unique request ID, connector
audience, binding ID and source reference. IDs are opaque bounded strings;
timestamps are timezone-aware UTC. Unknown fields and unrecognized versions
are rejected. Hashes are lowercase SHA-256 of the declared canonical source,
not a substitute for source ownership. Required fields cannot be silently
defaulted from another patient, visit or task.

Idempotency is scoped to actor, organization, facility, connector and operation.
A retry of an identical payload returns the original response. Reusing a key
with a different payload is a conflict. Source or report revision changes
require an explicit new operation. A timeout is an unknown outcome requiring
status reconciliation; it is not permission to create a second report.

Returned results identify the external record, immutable report revision/hash,
source hash/revision, reviewer identity and review state. AI suggestions,
human-confirmed values and signed reports are distinct states. Importing a
result never silently releases a HIS result, completes a task, signs a report,
or creates a referral. The HIS user reviews the exact returned revision first.

## DR receiver requirements

The derivative starts from original revision
`6ae2952b740165c9becc06964dddc93069a82028`; its independent baseline is
`02768b406c85bb82cfa472766464b3f838bf8291`. Full backend/frontend source and
license notices are retained. Credentials, patient images, sample media,
databases, weights and original Git metadata are excluded.

DR currently selects a workspace and case store for the application. Switching
that global workspace per HTTP request is prohibited. Receiver implementation
must either provide independently scoped application instances or prove
exhaustive case/workspace authorization across all reachable routes before
multi-patient access is enabled. Administrative workspace, source-import and
model-configuration routes are not exposed by a clinical launch.

Patient mapping, laterality, modality, admission and image confirmation remain
mandatory. Original pixel geometry, derivative lineage and source hashes are
preserved. Destination selection is separate from consent to send a particular
source. Existing consent, model identity, revision and stale-result checks
remain in force. Theme colors must not change clinical overlay semantics.

Initial tests use authored synthetic sources and injected providers. They
establish adapter behavior only. Live retinal inference requires its own
source/destination/model authorization and cannot reuse a historical grant.

## LabClear receiver requirements

Use a dedicated isolated CareBalance instance for connector validation; do not
deploy changes to the existing Render application as part of this checkpoint.
Preserve report ownership, business CSRF, staff branch scope, same-person
confirmation and the existing send → confirm values → understand → follow-up
journey. No iframe or cookie sharing is introduced.

The initial source is a HIS D10 laboratory result released through its existing
human workflow. Transfer exact analyte, printed value, unit and reference
range as strings, source revision/hash and provenance. Do not invent a normal
range, convert units, infer identity from a name, or treat an AI explanation as
a confirmed measurement. Corrections create a new source revision and require
review. Existing LabClear privacy-sharing gates remain unchanged.

## Acceptance matrix

| Boundary | Required evidence | Current status |
| --- | --- | --- |
| Original DR preservation | Source and Git metadata before/after hashes | PASS at baseline creation |
| Independent derivative | Own repository, no upstream credentials/state | PASS at baseline creation |
| LabClear visual adapter | Isolated delivery/contrast/workflow tests | PASS, actual isolated desktop/mobile preview; no live OCR/model claim |
| Scoped HIS LabClear binding | Cross-patient/facility/actor and stale-source negatives | PASS, independent PostgreSQL suites and private deployed HTTP journey |
| LabClear exchange | Expiry, audience, replay, session revocation, CSRF | PASS, bounded protocol/client/receiver/PG tests; no shared browser session |
| LabClear receiver API access | Every reachable route enforces current bound context | PASS, only three authenticated service routes plus readiness; default business surface absent |
| Lab result transfer | Exact values, ownership, retry and correction behavior | PASS, two-DB HTTP and actual browser42 to reviewed43; original42 retained |
| DR receiver access | Sealed patient/source-set, actor, capability and clinical route allowlist | ACTIVE implementation; runtime NOT_RUN |
| DR source/report round trip | Geometry, consent, revision, signed report boundary | NOT_RUN |
| Public acceptance | Authenticated synthetic journey through deployed URL | NOT_RUN for integrations |

Keep integration results separate from the already deployed HIS document-AI
workflow. Its existing evidence does not establish either new connector.
