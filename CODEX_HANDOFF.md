# Codex handoff — triadic UI and protected POC deployed

Local synthetic acceptance: 38 domains L2 and 10 journeys L3 PASS. Read VALIDATION_REPORT.md, DOMAIN_COVERAGE.json and JOURNEY_COVERAGE.json for the exact scope and evidence. The subsequent named real dr-train document route is recorded separately below; production and clinical acceptance remain NOT_RUN.

## Current deployed state — 13 November 2026

The owner resumed and authorized the named synthetic deployment. https://his.ai-cie.com is active behind exact-host Cloudflare Access. dr-train root /home/chaw/his-poc is a snapshot runtime, not a Git checkout. Dedicated Compose project his-poc-server uses app127.0.0.1:18080, DB127.0.0.1:15432 and connector metrics127.0.0.1:20331; existing private Ollama11434 is unchanged. The Windows source database/files remain independent.

Final image his-poc-server:triadic-778ba97bf46f has48 runtime-source and21 built-asset hashes matching the reviewed frontend/backend. Original109 table counts/one file and prior real result were preserved; final replacement retained test01 and178 prior sessions. Source publication does not automatically deploy.

Latest frontend25 unit/69 component, audit/typecheck/build,13 actual responsive observations and independent review PASS. Public browser test01→D22synthetic document→D37real Typhoon→human editv2→approve→commit→reload PASS; read-only server verification confirms one attempt/result. Run63506882-333c-479c-992e-027b991c836a took10414ms,422input/136outputtokens,costnull. Result ef4e9f7e-e0b2-473e-ab55-79ea383ffb72. These are integration checks, not clinical or throughput evidence.

Use docs/DEPLOY_DR_TRAIN.md and docs/RELEASE_TRIADIC_DEPLOYMENT.md before updates. Private server.env, source backups and tunnel credential stay outside Git. The owner-requested test01 password is not in artifacts; its account is clinician/patient-001 only, no admin/finance/wildcard. Global account policy and existing users were unchanged.

The dated local/pause sections below are historical; their palette/setup-pending statements were superseded by this deployment. Latest evidence: evidence/triadic-release/public-final and evidence/deployment-20261113.

## Application

- Target checkout: C:/Users/User/Desktop/myProject/his-poc.
- Default app: backend.app.main:app, /api/v2, React apps/web, PostgreSQL 18.6 and Alembic.
- Windows Docker app remains available at http://127.0.0.1:8000/login.
- Use synthetic account registration or another seeded role; obtain its private password from local .env. No credential is included in this repository.
- Restart with python scripts/dev.py start; no automatic seed or reset. Data and backup volumes are retained.
- Source repository: https://github.com/siriponsri/his-poc. The user authorized pushing main; the later explicit named-host authorization covers the deployed POC above.

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

No internal acceptance blocker remains in the reviewed local scope. Future external work requires named resources and session authorization. Hospital interfaces, production IdP, clinical deployment, payer certification and clinical/product evaluation remain NOT_RUN/UNKNOWN/NOT_CONNECTED as applicable. Baseline AI evidence is explicit DEMO mock; the named live document route below has actual inference evidence.

A repository-wide software license has not been selected. Third-party notices and generated-logo provenance are recorded separately.

## Real dr-train document route

Local private .env now opts into dr_train_ollama, while committed defaults remain mock_demo. Docker app on port8000 is running this explicit live synthetic profile. Existing SSH private-key configuration is used through a loopback-only forward; no key or endpoint identity is published. dev.py start verifies/starts that forward only when both live profile and tunnel opt-in are set. Read docs/DR_TRAIN_AI.md for native/Docker URL distinctions and pinned model/engine configuration. Migration0002 adds durable inference reservation/provenance without resetting data. A pre-migration backup is recorded under evidence/fullsystem/live-ai.

Actual Typhoon inference: three authored Thai cases PASS; browser document → task → five source-quoted checks → human edit v2 → approve → commit → reload PASS7, followed by read-only exact run-row PASS2. Sample run11.205s,408 input/141 output tokens,cost null. Evidence: apps/web/evidence/fullsystem/live-dr-train-final/browser-live-ai.json and live-dr-train-readback/browser-live-ai-readback.json. PostgreSQL17 orchestration tests use injected providers and are not extra real-model observations. Mock core18 and provider/tunnel/frontend regressions passed.

Never hold a database transaction across inference. Keep durable started/outcome rows, actor+key replay, one active inference across users/workers, absolute HTTP deadline, post-call permission/session/scope/source checks, and version-bound human approval. A client deadline closes transport; cancellation inside the remote engine is UNKNOWN. Exact quote checks do not prove semantic correctness. DR/CAD remain unconnected to live prediction. MedGemma is installed but not inference-tested. No model download, Cloudflare deployment or remote service restart was performed.

## Historical frontend refresh / Cloudflare pause handoff — 13 November 2026

The user superseded the green identity with yellow/gray/purple/orange using four supplied visual references and four inspected URLs. Incoming Claude working files were copied to ignored var/frontend-before-refresh before refinement. Preserve that backup; a local Vite design config remains ignored and is not the production deployment path.

Current app on8000 serves the rebuilt themed UI with the unchanged real dr_train_ollama backend profile. Frontend verification:25 unit/63 component plus audit/typecheck/build and runtime dependency audit PASS. Browser13 observations PASS on desktop1440 and mobile390, including persisted five-item live report and11205ms provenance; no new inference/domain mutation was performed. Runtime binding PASS45 files; readiness0002. Evidence: evidence/frontend-refresh/production-browser and final-themed. Initial stale greeting assertion failure remains under final-checks. Three reviewed accessibility/expansion defects were repaired and have regressions. Backend application code remains unchanged from dae61fc; new Cloudflare helper tests are separate.

The selected target is his.ai-cie.com. Read-only user-browser inspection confirmed ai-cie.com is present in the logged-in Cloudflare account with Full DNS setup and Active registrar status; no account state was changed and no private account IDs were saved in project artifacts. User said no Tunnel yet and requested manual setup instructions, then pause until they return.

Next: docs/CLOUDFLARE_SETUP_TH.md steps1–5. Private var/cloudflare/settings.json has hostname but still needs the owner's tunnelUUID/credential path/team/AUD. Do not ask for secrets in chat. New helper validates exact-host Access-required ingress, securecookie/HTTPS origin,90s transport deadline and private ports; local fixtures passed, actual account profile is not configured. Public DNS/tunnel/external workflow remain NOT_RUN. When owner resumes, inspect current files/state, validate private settings, retain backup and apply the HTTPS profile before starting a named connector; then execute external Access/login/scope/real-model/human-review acceptance. No implicit public publishing is claimed from this preparation.
