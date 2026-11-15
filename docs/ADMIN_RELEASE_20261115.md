# Administration console release

Status: **DEPLOYED_AND_ADMIN_ACCEPTED** on15November2026, Asia/Bangkok.
Runtime source `74795e2dc8a01f7fcc7f90132aa0acad0874e855`, immutable image
`sha256:416fbe75837265114f65c1b6ba7695a819e4c2edc7df743b5c08b65bb0267ede`,
schema `0005_assistant_workspaces`. The protected URL is
[his.ai-cie.com/admin](https://his.ai-cie.com/admin).

## What changed

The dedicated Administration workspace provides server-side user search/paging,
account status, persisted memberships and care assignments, session inspection/
revocation, and security activity. A persisted system administrator lands here
after normal login. Opening Administration does not prefetch patient or encounter
records. Clinical users retain their existing workspaces.

The overview reports organization user/session counts, current-facility denial
events and durable assistant-run counts. Provider configuration and qualified
profiles are distinct from live health: this page contacts no model and reads no
clinical bodies. Version conflicts require reloading the exact account; an
uncertain mutation retains its original semantic command for explicit retry.

The requested `admin` account was explicitly provisioned using the private
stdin-only CLI and existing password hasher. Normal API login and protected
browser login passed. Its single active `system_admin` membership does not
automatically grant clinical signing, document content, assistant preparation or
platform host operations. No credential is distributed in source. Public account
create/reset retains its12-character policy; the private named-POC exception is
documented in the [operator contract](ADMIN_OPERATIONS.md).

## Verification and limits

| Layer | Result | Exact scope |
| --- | --- | --- |
| Disposable PostgreSQL18.6 | PASS38 | 35new Admin cases and3existing authentication/J07/current-session permission regressions;15other core cases unselected |
| Mounted frontend | PASS171 | 15Admin cases plus156existing; real permission shape, scoped identities, conflicts/retry and dialogs |
| Frontend unit | PASS31 | Existing suite |
| Typecheck/build | PASS | Final CSS rebuild;20assets; existing chunk-size warning retained |
| Independent source review | PASS | Backend scope/provisioning, frontend recovery and final CSS containment; reported defects repaired |
| Candidate server qualification | PASS |315frozen source/dist inputs,20assets and153API paths under UID/GID10001; all backend/auth/AI/dependency bytes unchanged for the CSS followup |
| Isolated restored0005 | PASS | Generated test-only9-character credential, create/replay/login/scope/CSRF/public12policy; isolated containers removed; owner credential not used |
| Actual account/API | PASS | Private creation; normal login,5Admin reads, document403 and logout |
| Protected browser | PASS subset | Default/admin landing,22users, server search returning3matches, four sections, session identities independent of filtered directory, actual security events, create-dialog reading/close, responsive layouts |
| Mobile followup | PASS | Initial390px layout overflow492 retained; one CSS rule fixed positioned screen-reader header containment; final document width380at390, desktop1270at1280, mobile dialog inside10–370 |
| Runtime/preservation | PASS | Fresh cron-owned PID419519/start32006075, configa832c643, unchanged worker ENVbfacb7f0, original crontab, all source files and clinical/specialist records preserved |

Public browser create/reset/grant/suspend/revoke mutations were not performed.
Their current behavior is covered by the local PostgreSQL and mounted suites.
Desktop Escape and mobile close-button behavior passed; the browser tool could
not dispatch an Escape press to the mobile dialog, so that attempt is NOT_RUN.
The browser captured no console errors. Temporary viewport overrides were cleared.
No new AI generation, clinical write, watch activation, model evaluation or host
reboot was part of this release. The historical38domain/10journey baseline and
six real AI calls retain their original evidence limits.

## Deployment and preserved data

The first Admin image391df53 was ready at01:14UTC, the owner account/API acceptance
completed at01:15, and the first foreground worker proof completed at01:18. The
CSS followup416fbe75 was ready at01:28; fresh worker proof completed at01:29 and
the final read-only audit at01:31UTC. No schema migration or seed ran.

Compared with the pre-account baseline, exact additions were User1, Membership1,
SecurityEvent2, LoginAttempt2, SessionRecord2 and AuditEvent4. One existing test01
session changed only `revoked_at` through ordinary logout. All other original
session columns and120non-auth HIS tables were preserved. Every row in the
pre-CSS-deploy baseline remained unchanged through the CSS replacement.
LabClear2tables, DR10tables and3source files remained exact. Assistant counts
remain6runs/8revisions/5decisions/7effects/1pausedwatch; legacy inference/results
remain9/9. The dedicated engine, model, GPU and backend admission pins passed.

Unrelated research containers appeared during preparation. Their observed
additions were retained separately; no unrelated service was controlled. Access,
Tunnel and DNS were unchanged. The original crontab was restored byte-for-byte
after removing each exact owned one-off launcher.

Earlier rejected attempts remain distinct: source-test repairs, an incorrect
local-image build reference, missing candidate dist assets, an unrelated-container
preflight drift, old tag-versus-image selector validation, and overly strict UTC
directive checks. They stopped before the corresponding production mutations.
Only the identified passing images/phases were selected; no blind retry or model
call was used. The initial mobile failure and its native screenshot are retained.

## Recovery

Private fresh backups of all3databases were captured. Restoring those exact fresh
dump bytes is NOT_RUN; the separate previous0005isolated restore is PASS.
Reviewed recovery restores the previous391df53 app/config while preserving the
new administrator, audit and all current data. It handles a missing/stopped/
unhealthy app using a pinned readonly probe and the exact readonly HIS file mount.
Recovery execution and host-reboot acceptance remain NOT_RUN. Never rewind a
database or clear an unknown-dispatch marker to make an app rollback pass.

Latest server bootstrap witness:
`/home/chaw/his-poc/var/admin-release-20261115/mobile-followup/new-start-preexec.json`.
This supersedes the old witness for runtime identity checks; old evidence stays.

## Evidence and next work

- [Local qualification](../evidence/admin-20261115/local-qualification.json)
- [Isolated acceptance](../evidence/admin-20261115/actual-isolated.json)
- [Actual account/API](../evidence/admin-20261115/account-acceptance.json)
- [Final runtime](../evidence/admin-20261115/final-runtime.json)
- [Final row/file audit](../evidence/admin-20261115/mobile-followup/actual-final-readonly-audit-public.json)
- [Browser acceptance](../evidence/admin-20261115/browser-acceptance.json)
- [Native screenshots](../evidence/admin-20261115/screenshots.json)
- [API reference](admin/README.md), [product review](PRODUCT_REVIEW_20261115.md),
  [README visual provenance](README_VISUALS.md)

After this Admin acceptance, the owner added the illustrated in-app User Guide.
Its later implementation/deployment and reading evidence are recorded in
[User Guide release](RELEASE_USER_GUIDE.md); the Admin checkpoint retains its original scope.
