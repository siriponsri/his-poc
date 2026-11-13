# Codex handoff — v0.3.0 locally validated development prototype

Local synthetic acceptance: 38 domains L2 and 10 journeys L3 PASS. Read VALIDATION_REPORT.md, DOMAIN_COVERAGE.json and JOURNEY_COVERAGE.json for the exact scope and evidence. This is not production, clinical or L4 acceptance.

## Application

- Target checkout: C:/Users/User/Desktop/myProject/his-poc.
- Default app: backend.app.main:app, /api/v2, React apps/web, PostgreSQL 18.6 and Alembic.
- Windows Docker app remains available at http://127.0.0.1:8000/login.
- Use synthetic account registration or another seeded role; obtain its private password from local .env. No credential is included in this repository.
- Restart with python scripts/dev.py start; no automatic seed or reset. Data and backup volumes are retained.
- Source repository: https://github.com/siriponsri/his-poc. The user authorized pushing main; source publication does not authorize deployment.

## Executed evidence

The Windows full run is evidence/fullsystem/windows-final/execution.json. It passed 69 original PostgreSQL tests and 13 additional auth/clinical/ERP tests. Two separate live-Uvicorn locking/security tests and 10 current legacy-import tests also passed. Frontend: 25 unit and 53 component tests; launcher/helper units: 19 plus 4 subtests.

Browser indexes:
- apps/web/evidence/fullsystem/windows-browser-execution.json
- apps/web/evidence/fullsystem/windows-browser-journeys-aggregate.json
- apps/web/evidence/fullsystem/windows-browser-extra-domains-aggregate.json
- apps/web/evidence/fullsystem/windows-recovery-final/browser-recovery.json

These retain source reports/hashes and actual IDs. The 10 journeys are composed from successful scenario runs, not an assertion that every earlier run passed. Initial failures are preserved.

The UI-created backup/restore was verified independently using read-only database connections: evidence/fullsystem/windows-20261113/browser-restore-verification.json. It checks 109 tables including Alembic, one file, two persisted file references, and eight exact UI-created records. The isolated restore target is his_restore_023ee48338444e91a116beab132b9e46; the active database was not overwritten.

## Repairs and invariants

Preserve shared identity/scope, immutable evidence/proposal versions, authorization rechecks, atomic domain audit/ledger/idempotency and fail-closed provider selection. Imaging file download now requires content/export rights and records a bounded audit event. Support-entity audit reads use the existing actor-visible list policy.

Security-denial logging runs in a worker thread. Do not put blocking database operations back into async HTTP middleware: a denial's user FK can wait on another request's identity transaction and otherwise freeze the event loop. The live locking regression demonstrates continued health responses and eventual persisted denial audit.

Contracts/data dictionary were exported from runtime definitions, including all 13 ERP create/action schemas. Hash manifests describe actual delivered bytes; .gitattributes prevents newline rewriting.

## Continue safely

Reproduce on a new isolated synthetic environment before changing code. Use a fresh validation output directory and inspect every exit code. Browser scenarios now use fresh encounter records where repeat runs require them; retained failures must not be erased to improve status.

No internal acceptance blocker remains in the reviewed local scope. Future external work requires named resources and session authorization. Live inference, exact model/hardware/endpoint verification, hospital interfaces, production IdP, deployment, payer certification and clinical/product evaluation remain NOT_RUN/UNKNOWN/NOT_CONNECTED as applicable. All AI evidence here is explicit DEMO mock.

A repository-wide software license has not been selected. Third-party notices and generated-logo provenance are recorded separately.
