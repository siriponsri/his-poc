# Validation report — v0.3.0 local development acceptance

Date: 13 November 2026. Data: authored synthetic only.

**Local development target PASS: D01–D38 at L2 and J01–J10 at L3.** This combines executed PostgreSQL workflows, real rendered browser actions, negative cases, persistence and restore evidence. It does not certify clinical effectiveness, external integrations, or production readiness.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Windows Docker Linux-engine initialization | PASS: private init, config, up; migrations and explicit seed before readiness | evidence/fullsystem/windows-20261113/docker-up-retry.txt |
| Fresh PostgreSQL 18.6 migration and repeat seed | PASS; 108 application tables, 6 patients, 6 encounters, 4 tasks, 19 users, 23 memberships | evidence/fullsystem/windows-final/seed.txt |
| Core / clinical / ERP / operations | 18 / 25 / 13 / 13 PASS: 69 PostgreSQL tests | evidence/fullsystem/windows-final/execution.json |
| Additional auth / clinical / ERP acceptance | 3 / 5 / 5 PASS: 13 PostgreSQL tests | evidence/fullsystem/windows-final/execution.json |
| Live Uvicorn security-event concurrency and scoped staff audit | 2 PASS; health responds while denial audit waits on a real FK lock | evidence/fullsystem/windows-20261113/security-event-concurrency.txt |
| Legacy import into disposable PostgreSQL | 10 PASS; missing originals remain unavailable/quarantined | evidence/fullsystem/windows-20261113/legacy-current/execution.json |
| Launcher, encoding, contracts, packaging and browser helper units | 19 PASS and 4 subtests PASS | evidence/fullsystem/windows-20261113/launcher-final/launcher.txt |
| Frontend unit / React components | 25 / 53 PASS; components use jsdom | evidence/fullsystem/windows-final/frontend-test.txt; frontend-test-component.txt |
| Typecheck, audit regression, production build | PASS | evidence/fullsystem/windows-final/execution.json |
| Same-origin HTTP and server restart | 19 assertions PASS; separate from browser | evidence/fullsystem/windows-final/same-origin.txt |
| Real Chromium smoke | 11 assertions PASS on final image | apps/web/evidence/fullsystem/windows-smoke-accepted/browser-smoke.json |
| J01–J10 rendered journeys | 10 PASS, with exact actors, IDs and observed server responses | apps/web/evidence/fullsystem/windows-browser-journeys-aggregate.json |
| Additional rendered domains | 12 PASS, completing the 38-domain UI inventory | apps/web/evidence/fullsystem/windows-browser-extra-domains-aggregate.json |
| Browser conflict, delayed A→B context, audit, restart and UI restore | 9 assertions PASS | apps/web/evidence/fullsystem/windows-recovery-final/browser-recovery.json |
| Independent read-only inspection of that UI restore | PASS: 109 tables including Alembic, 1 file, 2 file references, 8 exact J01/J05/J08 records and image checksum | evidence/fullsystem/windows-20261113/browser-restore-verification.json |
| Running image/source binding | PASS: 27 backend and frontend-build files match the current worktree | evidence/fullsystem/windows-20261113/final-runtime-binding.json |
| Runtime contracts and data dictionary | 108 application tables, 129 paths, 67 schemas; clinical and all 13 ERP input contracts exported | contracts/v2/; docs/DATA_DICTIONARY.csv |

The 84 current PostgreSQL workflow/security tests and 10 legacy-import tests are separate from frontend/unit assertions. Repeated diagnostic reruns are not added to these totals. Fresh seed counts do not describe the current app, which also retains records created through the browser.

## Browser and source provenance

All browser mutations used visible React forms and actions against the same local PostgreSQL application. Observed responses supplied exact IDs; read-only denied navigations checked server authorization. D37 used explicit DEMO mock throughout.

Journey evidence is composed from recorded successful scenarios, with source reports, report hashes and runtime bindings retained per journey. J01–J08 preceded the final staff-audit visibility restriction; J09–J10, smoke, credential revocation and recovery ran on the final image. The affected own/other-staff authorization path also passed a live Uvicorn/PostgreSQL regression.

The full validation command completed all 16 selected checks with exit code 0. Its run-manifest openly lists changes made while it ran, including the staff-audit restriction and test/harness files. The separate scoped regression, final runtime binding and per-scenario browser evidence cover those changes; the run is not represented as a frozen, unchanged source snapshot.

## Failures retained and repaired

The incoming checkpoint had not executed browser or Windows/Docker acceptance. This session reproduced and repaired Docker web-build prerequisites, Windows npm invocation and UTF-8 handling, native fetch receiver binding, nonexistent audit/support detail requests, integer sequence serialization, the dispensing stock-location selector, referral download visibility, imaging-file permissions/audit, and synchronous denial logging that could freeze the event loop while waiting on a database lock. Staff audit reads now follow the existing staff visibility policy.

Harness failures from asynchronous locators/response observation, missing required human-review evidence, and incorrect expected denial/route/serialization details were corrected without bypassing forms, weakening backend validation, or relabeling failed runs. Original failures, screenshots and command exit codes remain in evidence. The browser execution index records 20 observed runs, including failures.

A Playwright teardown warning occurred after the final recovery assertions; its process exited 0. Deprecation warnings from TestClient/httpx and Alembic were observed. Neither warning is counted as an application assertion.

## Scope that remains separate

- MOCK: all AI proposals and DR-related review integration. No live model was invoked; measured live cost remains unknown/null.
- NOT_RUN / NOT_CONNECTED: live inference, payer/national/HIS/LIS/PACS connectors, training, deployment, production/server changes, hospital SOP acceptance, clinical/product effectiveness.
- UNKNOWN: external endpoints, hardware and exact Qwen/Typhoon/MedGemma checkpoints/revisions.
- The native application launcher alternative was not needed; the chosen Windows Docker path and native disposable PostgreSQL test path were executed.

DB12 behavior across live external inference remains NOT_RUN with live routes disabled. Local mock integration does not establish that future live-provider behavior.

## Reproduction and release integrity

Follow START_HERE.md. The validation runner accepts --output-dir to preserve earlier evidence. Browser scripts support --help safely and require private HIS_SEED_PASSWORD from the local .env, never a public demo token.

Regenerate contracts with scripts/export_contracts_v2.py, check consistency with scripts/check_fullsystem_package.py, and package reviewed tracked files with scripts/package_release.py. SHA256SUMS.json excludes itself; ZIP CRC and every included source hash are verified. .gitattributes preserves exact bytes across Git checkouts.

Initial checkpoint documents are retained under evidence/fullsystem/windows-20261113/initial-docs/. The dated matrix review remains historical; current coverage and executed evidence control local acceptance.
