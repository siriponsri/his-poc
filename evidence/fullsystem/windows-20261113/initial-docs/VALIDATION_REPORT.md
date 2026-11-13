# Validation report — v0.3.0 checkpoint, 2026-11-13

ผลส่งมอบ: IMPLEMENTED DEVELOPMENT CHECKPOINT. ยังไม่ประกาศ full-system acceptance: domain workflows มีโค้ดและ PostgreSQL tests แต่ browser L2/L3 acceptance ยัง NOT_RUN. Canonical target38domains/10journeys ไม่เปลี่ยน.

| Check | Observed result | Evidence |
|---|---|---|
| PostgreSQL18 migration + deterministic repeat seed | PASS;108application tables;6patients/6encounters/4tasks/19users/23memberships | final/seed.txt; data/POSTGRES_SEED_MANIFEST.json |
| Core/auth/evidence/proposal | 18 PASS; Alembic no drift | final/core.txt |
| Clinical domain workflows | 25 PASS | final/clinical.txt |
| ERP/ledger/stock workflows | 13 PASS | final/erp.txt |
| Operations/restore/authorized CLI | 13 PASS | final/operations.txt |
| Launcher unit checks | 6 PASS | final/launcher.txt |
| Real TCP same-origin app | 19 assertions PASS incl server restart persistence | same-origin/result.json |
| Frontend unit | 24 PASS | final/frontend-test.txt |
| React/jsdom components | 49 PASS, not browser | final/frontend-test-component.txt |
| Audit regression | PASS; baseline3 defects, patched0 | apps/web/evidence/fullsystem/baseline-reproducer.json and fixed-reproducer.json |
| TypeScript and production build | PASS | final/frontend-typecheck.txt; final/frontend-build.txt |
| OpenAPI/dictionary export |108tables,129paths,67schemas | contracts/v2/openapi.json; docs/DATA_DICTIONARY.csv |
| Legacy import baseline |10 PASS in prior isolated run, not counted in69 final PG tests | baseline/legacy-import-pg.txt |

Paths abbreviated above are under evidence/fullsystem unless explicitly prefixed otherwise. Final execution.json preserves command, exit status, duration and log. First package check failed while release docs were incomplete and its route inspection needed adaptation to FastAPI included routers; package-recheck.json records the subsequent corrected result without erasing the failure. Final core+clinical+ERP+operations =69 actual PostgreSQL tests. Same-origin smoke is HTTP, not rendered UI.

J01–J10 HTTP/PG evidence preserves linked record IDs in JOURNEY_COVERAGE.json. These are synthetic/manual workflows. D37 uses explicit DEMO mock; no real model was invoked. Component mocks are disclosed and do not demonstrate backend connectivity. API integration evidence and clinical/product effectiveness remain separate.

NOT_RUN: Chromium browser journeys/visual/responsive acceptance (preflight failed socket Operation not permitted,0 assertions); Docker Compose execution (runtime unavailable); Windows/PowerShell execution; live cloud/dr-train/local inference; actual payer/national/HIS connectors; clinical/product effectiveness. Browser scripts are authored, not passed. Hardware, endpoint and exact checkpoint/revision remain UNKNOWN. No paid API/training/deployment performed.

Independent matrix review is a dated source snapshot. Later clinical fixes include DeviceAssignment lifecycle and domain-specific history/concurrency tests; final25 clinical tests verify the updated implementation. D26 uses manual local allocation policy; D33 local reporting definition only; D24 synthetic local reconciliation is not payer certification. External integration remains NOT_CONNECTED.

Reproduce: install locked requirements and npm ci, run python scripts/validate_fullsystem.py --pg-bin <PG18_BIN> --include-frontend. This creates disposable synthetic clusters. Then follow START_HERE to start an isolated real app and run apps/web/scripts/browser_check.py and browser_journeys.py (read --help). Never point test suites at production. Deprecation warnings from TestClient/httpx and npm proxy config were observed; no failed application assertions from those warnings.

Consistency checked against GOAL/PLAN/AGENTS/BACKLOG, canonical matrix, exported runtime contracts, provider/routing config and current coverage. Status is conservative: implementation is present, full L2/L3 acceptance pending. Historical v0.2 documents are archived, not controlling scope.
