# Codex handoff — v0.3.0 Full-system checkpoint

Default app: backend.app.main:app, API /api/v2, PostgreSQL18 + Alembic; React apps/web. Historical v0.2 source and tests remain but /api/v1 is not mounted. Read START_HERE for exact initialization and non-seeding restart commands.

Implemented: multi-entity scoped core, 18 clinical and 13 ERP domains plus operations; 108 application tables; opaque server sessions, permission checks, explicit mock proposal/review/commit, immutable evidence/audit, stock/finance ledgers, operations jobs and isolated restore. DOMAIN_COVERAGE and canonical spec are authoritative for acceptance boundaries. Current status is checkpoint, not completed L2/L3 certification.

First task: reproduce local startup and execute browser J01–J10 on a host with working Chromium. See STARTER_PROMPT_TH.md. Native PostgreSQL/HTTP/component results do not replace browser acceptance. Docker and Windows startup remain NOT_RUN in this environment. Keep any failing command and resolve the failure before upgrading status.

Evidence: evidence/fullsystem/final/execution.json contains final integration commands/logs. Older evidence has its own execution time/source hashes; independent_review.md is a dated snapshot, not a statement that later corrections were absent. DeviceAssignment and follow-up regression fixes landed after that review. See VALIDATION_REPORT.md.

Use scripts/export_contracts_v2.py after API/model edits; migrations, not schema-reference.sql, initialize DB. Recheck GOAL/PLAN/AGENTS/config/contracts/BACKLOG, run scripts/check_fullsystem_package.py, regenerate SHA256SUMS only after final edits. No paid inference/deployment authorized by this handoff. Unknown model checkpoints/endpoints remain UNKNOWN. External/manual/synthetic workflows must not masquerade as connected services.
