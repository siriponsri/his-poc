# Expanded patient-record panel candidate

This records the panel/real-AI public workflow phase. A subsequent scroll-only
follow-up supersedes its active image; see `../scroll-reset/READINESS.md` for the
final activation and retained-result readback. Phase-specific evidence is preserved.

Scope: owner-requested wide patient subpanel, source readability and user journey,
with canonical D37 document URL context and a closed-task guard on fresh inference.
Backend/deployment configuration remains unchanged. This is a subsequent UI-only
update, preserving the earlier workspace deployment receipts one directory above.

The new freeze references
`apps/web/evidence/patient-record-panel-20261114-final/checks.json`:25 unit,
89 component,3 audit cases, typecheck and build passed.

Snapshot SHA256:
`86b174ff10c5f7bda6ef290fe07892f06cd458ac4584953509353a47e1fae236`.
Image: `his-poc-server:workspace-86b174ff10c5`.
Image ID: `sha256:5fdd760121dc8db0e7e233b7b8cee6d4e575b3f23f515cec1f28971680f2c63c`.

`built-image-source-binding.json` confirms214 source files and17 built assets match
the frozen Windows source/build, including all three self-hosted fonts and licenses.
This inspection ran in a disposable network-isolated read-only container; it did
not start the application, connect to the database or perform inference.

Fresh read-only baseline:109 tables, one stored file, both prior committed live
results, unchanged test01 scope and179 existing sessions including the owner's new
login. Actual activation requires another fresh preactivation state and backup.

Rollback target for this cycle: `his-poc-server:workspace-072a759f371d`,
image ID `sha256:cd6f108817aa65663c7bc2842bcc40242356b15924015a7a266e62a1e5aae211`.
Rollback changes only the private image selection and recreates app; database/files,
connector, DNS, Access, accounts and Ollama remain intact.

## Activation

The parent authorized activation after independent source and rendered panel review.
`activation.json` records a fresh database/files backup at
`/home/chaw/his-poc/var/backups/pre-workspace-86b174ff10c5-20261114T023005Z` and
successful replacement of only the app. No restore, seed, account change or
connector restart occurred. Rollback was not needed.

`postactivation-preservation.json` passes13 checks, including all179 prior session
rows unchanged, test01 account/scope, both prior committed results, the exact stored
file,109 nondecreasing table counts, unchanged database/connector containers,
four private listeners and four connector HA connections.

`runtime-source-binding.json` verifies all214 active source hashes and17 built
assets match the frozen source/build. `origin-assets.json` confirms seven actual
HTTP responses (Login, CSS, JS, three fonts and logo) match local dist byte-for-byte.
The five unauthenticated public checks still redirect to Cloudflare Access, including
an invalid assertion: `public-access-boundary/access-boundary.json`.

## Public workflow readback

After the root's authenticated Chrome synthetic document/AI/edit/approve/commit
workflow, the separate read-only PostgreSQL receipt passes16 checks:
`../../patient-panel-public/public-workflow-readback.json`.
Run `9b797df1-18b5-4537-b036-b37cf8d337ca` used the pinned real Typhoon route,
took11563ms,424 input/134 output tokens, measured cost null. Four checklist entries
have exact source quotes; plan is missing. Human edit created immutable version2,
approval bound its hash, and exactly one result was committed:
`64d8a1ae-958c-4c33-a4e8-fa222c1e8448`. Stored idempotency replay matches the result.
This is synthetic workflow integration evidence, not clinical correctness.

`post-public-preservation.json` passes11 further checks, retaining both old results,
file checksum, test account/scope, all179 prior session IDs and unchanged database/
connector containers. Legitimate public workflow writes are expected; table-row
equality and unchanged session state are not asserted after browser actions.
Active214 source and17 asset hashes were rechecked successfully afterward.

Status: DEPLOYED_AND_PUBLIC_WORKFLOW_READBACK_VERIFIED. Root owns final rendered
browser acceptance and screenshots; deployment/readback receipts remain distinct.
