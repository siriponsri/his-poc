# Scroll reset: final UI-only follow-up

The authenticated public panel/real-AI workflow passed on the preceding89-component
candidate. The final follow-up repairs route/Login/logout viewport reset so the
Login logo remains visible after leaving a scrolled workspace; closing a patient
panel preserves its list position. Backend, core AI, source/version bindings and
deployment configuration are unchanged.

Frozen checks: `apps/web/evidence/patient-record-panel-scroll-20261114-final/checks.json`,
25 unit/91 component/3 audit cases plus typecheck/build PASS.

Snapshot SHA256: `167d14addf47841efa40298098aa1552761518eee3c99acd2e329fde3da16d87`.
Image: `his-poc-server:workspace-167d14addf47`.
Image ID: `sha256:56821a7a82ae714f7bfc039ef82e35ad51c4d0b5f91d89c5d5d816de8cb9210b`.

The disposable network-isolated image inspection passes214 source hashes and17
dist assets against the frozen source/build. The first read-only baseline retains
109 tables, one stored file,180 sessions, test01 scope and three committed results,
including public result `64d8a1ae-958c-4c33-a4e8-fa222c1e8448`.

Rollback target: `his-poc-server:workspace-86b174ff10c5`, image ID
`sha256:5fdd760121dc8db0e7e233b7b8cee6d4e575b3f23f515cec1f28971680f2c63c`.
Take another fresh preactivation state and database/files backup before replacing
only app. Never restore/seed/reset accounts, restart connector, change DNS/Access
or touch other dr-train projects/services. Final verification reuses the exact
public workflow run read-only; no additional inference is required for this fix.

## Final activation and readback

The parent authorized activation after independent review of the91-component final
freeze. Fresh database/files backup:
`/home/chaw/his-poc/var/backups/pre-workspace-167d14addf47-20261114T024310Z`.
`activation.json` confirms only app was replaced; no restore, seed, account change,
connector restart or unrelated service change occurred. Rollback was not needed.

`postactivation-preservation.json` passes13 checks, including all180 preexisting
session rows unchanged, three committed results including public result64d8a1ae,
test01 account/scope, file hash,109 nondecreasing table counts and unchanged database/
connector container IDs. All four endpoints remain loopback; connector has four HA
connections. These are point-in-time comparisons before further browser actions.

`runtime-source-binding.json` passes214 active source and17 dist asset hashes;
`origin-assets.json` passes seven actual HTTP responses matching local dist.
The final five unauthenticated public checks still redirect to Access, including
the invalid assertion (`public-access-boundary/access-boundary.json`).

`prior-public-workflow-readback.json` repeats all16 read-only checks of the exact
earlier public run9b797df1 after the swap. Version2 approval, exact source quotes,
canonical result64d8a1ae, idempotency replay and exactly one attempt/result remain
valid. No additional inference was performed for this scroll-only follow-up.

Status: DEPLOYED_AND_RECHECKED. Parent owns final rendered Login/Home/panel/retained
result smoke on this image; earlier public real-model browser workflow remains
separately bound to its preceding89-component source phase.
