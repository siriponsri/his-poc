# Validation report — v0.3.0 local development acceptance

Date: 13 November 2026. Data: authored synthetic only.

**Local development target PASS: D01–D38 at L2 and J01–J10 at L3.** This combines executed PostgreSQL workflows, real rendered browser actions, negative cases, persistence and restore evidence. It does not certify clinical effectiveness, external integrations, or production readiness.

## Baseline local checks (before the live document extension)

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

All browser mutations used visible React forms and actions against the same local PostgreSQL application. Observed responses supplied exact IDs; read-only denied navigations checked server authorization. D37 used explicit DEMO mock throughout these baseline journeys. Subsequent actual live document evidence is separate below.

Journey evidence is composed from recorded successful scenarios, with source reports, report hashes and runtime bindings retained per journey. J01–J08 preceded the final staff-audit visibility restriction; J09–J10, smoke, credential revocation and recovery ran on the final image. The affected own/other-staff authorization path also passed a live Uvicorn/PostgreSQL regression.

The full validation command completed all 16 selected checks with exit code 0. Its run-manifest openly lists changes made while it ran, including the staff-audit restriction and test/harness files. The separate scoped regression, final runtime binding and per-scenario browser evidence cover those changes; the run is not represented as a frozen, unchanged source snapshot.

## Failures retained and repaired

The incoming checkpoint had not executed browser or Windows/Docker acceptance. This session reproduced and repaired Docker web-build prerequisites, Windows npm invocation and UTF-8 handling, native fetch receiver binding, nonexistent audit/support detail requests, integer sequence serialization, the dispensing stock-location selector, referral download visibility, imaging-file permissions/audit, and synchronous denial logging that could freeze the event loop while waiting on a database lock. Staff audit reads now follow the existing staff visibility policy.

Harness failures from asynchronous locators/response observation, missing required human-review evidence, and incorrect expected denial/route/serialization details were corrected without bypassing forms, weakening backend validation, or relabeling failed runs. Original failures, screenshots and command exit codes remain in evidence. The browser execution index records 20 observed runs, including failures.

A Playwright teardown warning occurred after the final recovery assertions; its process exited 0. Deprecation warnings from TestClient/httpx and Alembic were observed. Neither warning is counted as an application assertion.

## Named real dr-train document route — 13 November 2026

The user authorized inspecting the existing server and connecting real AI to synthetic document completeness. This extension is separate from the baseline 38-domain/10-journey results above. No paid API, model download, shared remote service restart, training, Cloudflare deployment or real patient data was used.

| Check | Result | Evidence |
|---|---|---|
| Server and installed model discovery | Existing Ollama0.12.6; Typhoon12B and MedGemma27B manifests; V10032GB and RTX2080Ti11GB observed | evidence/fullsystem/live-ai/dr-train-inventory.json |
| Real protocol probe | Typhoon JSON response PASS; GPU-backed resident model observed | evidence/fullsystem/live-ai/typhoon-protocol-probe.json |
| Real provider cases | 3 authored Thai examples PASS: complete, missing plan, missing author; source quotes validated | evidence/fullsystem/live-ai/real-provider-cases.json |
| Actual live React workflow | PASS7: document/task → real model → typed five-item checklist → human edit/version2 → approve → commit → reload | apps/web/evidence/fullsystem/live-dr-train-final/browser-live-ai.json |
| Exact persisted run-row readback | PASS2; no further inference/domain mutations | apps/web/evidence/fullsystem/live-dr-train-readback/browser-live-ai-readback.json |
| PostgreSQL live orchestration | 17 PASS with injected deterministic providers; these are not extra real-model observations | evidence/fullsystem/live-ai/final/execution.json |
| Default mock core regression + migration drift | 18 PASS; no Alembic drift | evidence/fullsystem/live-ai/mock-core-regression/execution.json |
| Provider/tunnel/operations/launcher/contracts/browser CLI units | 57 PASS +5 subtests; includes slow-chunk absolute deadline regression | evidence/fullsystem/live-ai/final-static/execution.json |
| Frontend | 25 unit /60 jsdom component PASS; audit/typecheck/build PASS | evidence/dr-train/frontend-ui/execution.json |
| Pre-migration backup and in-place upgrade | Backup PASS; migrated0002 without seed/reset | evidence/fullsystem/live-ai/pre-migration-backup.json; docker-live-start.txt |
| Running backend/build source binding | PASS13 files; readiness reports0002 | evidence/fullsystem/live-ai/final/runtime-binding.json |
| Independent source review | Both P2 findings resolved; no remaining actionable blocker in reviewed scope; reviewer did not independently rerun tests | evidence/fullsystem/live-ai/independent-review.json |

The selected artifact is hf.co/scb10x/typhoon2.1-gemma3-12b-gguf:Q4_K_M, pinned to Ollama manifest digest ab914ef406c9a78e2a8893eaa3b0ef78049f6c4e2703626433028e838d3a168b and engine0.12.6. The existing GGUF source Hugging Face commit is UNKNOWN. Q4_K_M is the installed tag; runtime reports quantization unknown, so independent quantization verification is not claimed. Installed MedGemma was not inference-tested.

The actual browser run ID2e8c3ec9-11e9-4073-99b6-6a6c731bbe3e took11205ms with408 input/141 output tokens and cost null. Result ID8d61f05f-6b07-45d6-8d76-dc3296693dbb remained after reload. This is one observed run, not a latency guarantee or pricing measurement. Checklist headings are chief complaint, history, recorded assessment, recorded plan and author; they do not judge treatment or clinical correctness.

DB12 transaction release and current-state revalidation were exercised using actual PostgreSQL plus injected blocking providers, including NOWAIT identity locking and idle-transaction inspection. Same-key pending/replay/conflict, cross-user admission, stale document/task/encounter/domain, revoked session, expired lease, and retained failed/timeout/invalid/abstained outcomes passed. Final real-browser evidence additionally traversed the actual remote call. Closing the client transport on the absolute deadline does not prove the engine cancels server computation.

The original live browser harness failed on selector/helper usage before its first proposal request; its FAIL remains under apps/web/evidence/fullsystem/live-dr-train/ and evidence/fullsystem/live-ai/browser-live-execution.json. Corrected workflow and read-only reports are separate. The initial domain-fence regression and subsequent repair are retained in pg-evidence-index.json. The final17-test suite passed on frozen backend source. Later documentation, registry and validation-launcher changes are disclosed by their own source snapshots; no earlier run is backdated.

## Scope that remains separate

- Default committed configuration: explicit DEMO mock; the owner's private local .env explicitly selects real synthetic dr_train_ollama.
- Verified named external scope: document_review completeness only. DR/CAD live prediction, other model inference and clinical/semantic accuracy are NOT_RUN.
- NOT_RUN / NOT_CONNECTED: payer/national/HIS/LIS/PACS connectors, production IdP, training, deployment, hospital SOP acceptance and clinical/product effectiveness.
- UNKNOWN: original GGUF Hugging Face revisions, general real-world model quality, engine-side cancellation and live cost. Unknown values remain null.
- The native application launcher alternative was not needed; the Windows Docker app and native disposable PostgreSQL tests were executed.

## Reproduction and release integrity

Follow START_HERE.md. The validation runner accepts --output-dir to preserve earlier evidence. Browser scripts support --help safely and require private HIS_SEED_PASSWORD from the local .env, never a public demo token.

Regenerate contracts with scripts/export_contracts_v2.py, check consistency with scripts/check_fullsystem_package.py, and package reviewed tracked files with scripts/package_release.py. SHA256SUMS.json excludes itself; ZIP CRC and every included source hash are verified. .gitattributes preserves exact bytes across Git checkouts.

Initial checkpoint documents are retained under evidence/fullsystem/windows-20261113/initial-docs/. The dated matrix review remains historical; current coverage and executed evidence control local acceptance.
