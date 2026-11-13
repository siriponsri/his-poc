# HIS POC full-system engineering instructions

Read START_HERE → GOAL → PLAN → BACKLOG → CODEX_HANDOFF → VALIDATION_REPORT → DOMAIN_COVERAGE/JOURNEY_COVERAGE → spec matrix and relevant contracts. Inspect actual repo/branch/status and preserve user edits. This project began as an isolated copy from v0.2. The user authorized source publication to https://github.com/siriponsri/his-poc on main on 2026-11-13; that authorization does not extend to deployment or production changes.

## Authorized scope

The current user explicitly replaces singleton-only scope with PostgreSQL-backed multi-patient/encounter/task workflows, real local login/session/permissions, all38 domain minimums and J01–J10. Implement and test ready milestones continuously. Never use historical first-slice restrictions to reduce current scope. docs/history and legacy src are historical only. UNKNOWN external resources block their own connectors, not internal development.

Parallel agents are authorized with one integrator and non-overlapping files. Core owns identity/shared schema/contracts; modules import them and do not duplicate tables/auth. Agree DTO and transaction ownership before parallel mutations. User permits shadcn/ui, Magic UI, shadcn-admin and impeccable references; retain actual license/revision/provenance for copied code. Approval to reuse is not proof of copying or license verification.

## Invariants

- FastAPI modular monolith + PostgreSQL18 primary + SQLAlchemy/Alembic; SQLite only isolated legacy tests/import. Never silently fallback.
- Backend and service/tool boundary verify server identity, effective permission and organization/facility/patient/encounter scope on read/write/export/actions. Admin is not clinical signer. Portal owns one server-linked subject. Revalidate mutations against current permissions.
- Session cookie HttpOnly, explicit loopback dev HTTP setting; HTTPS Secure profile; CSRF on mutations. No credentials/session in frontend storage/bundle. No demo bearer bypass in default app.
- Immutable document revisions and proposal action/evidence snapshots; reviewer edits require new version and approval. Commit rechecks current status/version/hash/evidence/permissions. Domain write/result/audit/idempotency atomic. Retry cannot duplicate dispensing, stock, payment or result.
- Domain-specific typed forms/actions and state guards are required; generic JSON editor or generic task CRUD is not completion. Money/quantity use Decimal/DB constraints and immutable posting/movements. Net_received=gross_received-refunded; outstanding has its own allocation/adjustment policy.
- AI defaults to explicit mock synthetic profile. The user authorized the named dr_train_ollama synthetic document_review route; its exact identity and evidence are in docs/DR_TRAIN_AI.md. No silent fallback to mock/cloud. Live cloud requires both data policy and authorized budget. Model ID/SDK/endpoint belong adapters/registry, not business logic. Do not hold DB transaction across live external inference.
- Keep failure/timeout/abstention/edits and measured costs; unknown cost null. Declared capability differs from tested. DR/CAD each retain own contract/evaluator. Integration is not clinical effectiveness.
- Preserve legacy IDs/hash/results/audit; quarantine missing original revisions, never fabricate old text or alter hash to pass import. No new commit from unavailable evidence.
- Startup does not seed/reset. Migrate explicitly; seed explicitly and idempotently. Fail fast on migration error. Backup restore only isolated target, verify DB+files+hashes before claiming success.

## Evidence and handoff

Run tests appropriate to changed code on actual PostgreSQL. Distinguish legacy/component/build/browser/PG/live/clinical results. Skipped or blocked is NOT_RUN, not PASS. Report per-domain implementation_status, verified_level, verification_status, external_integration_status. Full completion requires all38 L2 and10 L3; otherwise checkpoint with specific gaps. Update GOAL/PLAN/architecture/contracts/config/backlog together. No paid APIs/training/deploy/real server changes without scoped authorization.
