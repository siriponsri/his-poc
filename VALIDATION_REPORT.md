# Validation report — User Guide, Admin and protected acceptance

## Active goal — AI evidence, team queue and Admin AI monitoring

Owner-authorized 15 November 2026. Status: IMPLEMENTING; no new deployment or
live acceptance claimed. Baseline c47868a remains the retained public release.
See [the frozen contract](docs/AI_TEAM_OPERATIONS_CONTRACT.md).

1. Implement profile-ranked exact source passages, original-revision evidence
   reading and measured selection/quote coverage; preserve the current model,
   prompt/schema limits, authorization and immutable review workflow.
2. Implement server-paginated accountable work with eligible claim/handoff,
   operational due dates and one-task escalation; keep domain completion guards.
3. Implement read-only Admin AI metadata with truthful timestamps, unknown
   heartbeat/freshness and scalar allowlists; no chart bodies or host control.
4. Qualify PostgreSQL/schema compatibility, frontend and independent review,
   then explicitly migrate/deploy the synthetic dr-train POC and test the real URL.

New live acceptance is bounded to at most eight application generations,
including two corrective reserves; no automatic retries/watch trial/cloud calls.
Old qualification and public evidence below retain their original scope.


## Illustrated in-app User Guide — 15 November 2026

Status: DEPLOYED_AND_GUIDE_ACCEPTED for the synthetic protected POC.
Runtime source 65c5bc5 / image 92166e35 / schema 0005 serves /guide. The guide
opens from login, the workspace header or sidebar; static help remains readable
without an HIS session after the existing Cloudflare Access gate.

It includes 16 chapters/101 task steps, 38 domain references/152 working steps,
11 exact synthetic screenshots and 10 paused-by-default explanatory walkthroughs.
Search, shareable chapter/domain links, role-oriented navigation, image zoom,
keyboard scrolling and mobile contents return are implemented. Guide controls
do not submit clinical work, change roles or request model generation.

PASS on base f962196: 31 frontend units and 195 mounted cases (20 guide + 4 shell).
Final source 65c5bc5 changes one heading CSS rule; its typecheck/build, independent
narrow review and protected desktop/mobile heading recheck passed. Content/media
validation and the remaining native reading checks passed separately. Protected acceptance and current runtime are recorded separately in
[User Guide release](docs/RELEASE_USER_GUIDE.md) and
[browser evidence](evidence/user-guide-20261115/browser-acceptance.json).
The Admin account, workflows, AI source/configuration and specialist services
remain preserved. This is a guide release, not new clinical/model effectiveness.


## Retained Administration release — 15 November 2026

Status: DEPLOYED_AND_ADMIN_ACCEPTED for the named synthetic POC. Runtime source
74795e2 / immutable image416fbe75 / schema0005 is ready behind existing Access.
The requested admin account was privately provisioned and normal login passed.
Dedicated /admin covers users, memberships, sessions and security activity,
without initial clinical-signing or platform-operator grants.

Local checks passed38PostgreSQL18.6 cases,171mounted frontend checks,31unit
checks and typecheck/build. Protected-browser acceptance covered login/default
landing, search, four sections, create-dialog reading/close and desktop/mobile
layout. An initial390px overflow was retained and repaired with one CSS rule;
the final live mobile readback passed. No public user-management mutation was
performed beyond the separately evidenced private account provision/authentication.

The same AI source/configuration and prior6runs/8revisions/5decisions/7effects
remain; this Admin release issued no model generation. Historical broad-domain,
AI and specialist evidence below retains its original scope.
See [Admin release](docs/ADMIN_RELEASE_20261115.md),
[runtime proof](evidence/admin-20261115/final-runtime.json),
[browser acceptance](evidence/admin-20261115/browser-acceptance.json) and
[product review](docs/PRODUCT_REVIEW_20261115.md). The roadmap is proposed work.


## Retained AI-driven acceptance before the Admin release

Status: DEPLOYED_AND_APPLICATION_ACCEPTED for the named synthetic POC scope.
Runtime source286f391 / immutable image9afd73f2 / schema0005 is deployed behind
the existing Access policy at https://his.ai-cie.com. Login, wide Patient record,
realistic fictional patients, LabClear and the separate DR derivative remain.
Operations opens in2D; explicit3D rendered on the protected URL and its room
opened the same saved visit. The3D scene is illustrative, with no staff tracking.

The foreground cron-owned assistant guard was observed from fresh SSH at17:57
UTC, with matching PID/startticks/cgroup/config/privateENV/image. The exact owned
one-off was removed and persistent reboot approval recorded. No reboot was run.
This is separate from actual inference: six normal-application Typhoon calls
completed with bound terminal evidence, using existing clinician/nurse/
registration/laboratory roles and no permission changes. Four preparation
profiles passed source-fidelity review. The original nursing test-only input was
preserved unapplied; one explicitly reviewed reserve call used a better authored
synthetic handover. No automatic retry, cloud fallback or held-image inference.

Five accepted decisions saved seven effects: two draft documents, two new
follow-up tasks and three links to existing review tasks. Human edits remained
new revisions; actual identical-key HTTP replay for nursing/records/laboratory
created no duplicate effects. Records used metadata only; nursing had no lab
source access. Nine actual role/scope reads passed expected403/404/metadata
boundaries. The protected public browser covered one visit: queue → evidence →
full omitted note → explicit demonstration edit → apply → full reload. Other
role workflows were normal authenticated production API checks, not separate
public-browser role acceptance.

An unchanged records watch caused zero automatic runs during its observed scan
window. One explicit authored source revision caused one new run; its reviewed
effect reused the original records task. The watch is paused with count1.
The source change intentionally leaves earlier visit/records artifacts stale;
saved old drafts/evidence remain. Page reads,2D/3D navigation, apply and replay
do not dispatch inference. Runtime app/worker remain enabled for explicit use.

Read-only18:12 preservation passed all old126HIS/2LabClear/10DR table rows, source
files, legacy configuration and non-app service identities. HIS additions are
explicit test records, not overwritten baseline rows. Historical InferenceRun9
(3REAL +6mock) and nine results remain separate from the six new AssistantRuns.
The original DR repository and LabClear owner edits remain preserved; ten renamed
MMRDR images remain held for laterality as the owner requested.

Evidence: [application acceptance](evidence/ai-driven-root-20261114/application-acceptance.json),
[deployment](evidence/ai-driven-root-20261114/deployment-readback.json),
[public screenshots](evidence/ai-driven-public-20261114/),
[release guide](docs/RELEASE_AI_WORKSPACE.md).
Final local source checks passed187 disposable PostgreSQL18.6 cases,156 mounted
frontend checks,31unit checks, typecheck/build; these are not a rerun of all38
domains. The older broad-suite failure and isolated resolution remain retained.
Two neutral infrastructure calls and five direct qualification calls are separate
from application calls; that direct budget is exhausted. Application trial used6
of7, including one source-correction reserve; no remaining trial call is automatic.

Limits: measured provider times50.579–56.381s, not a benchmark/SLA; monetary cost
is unmeasured/null. Outputs largely copy included short notes or select title/DOB
facts. Visit/nursing compact inputs omit records and require full-chart review.
This does not establish clinical effectiveness, measured staff-time savings,
all38domains using realAI, MedGemma27B/DR inference or host-reboot acceptance.
Direct fixture evidence, actual application effects and clinical validation must
remain distinct. Current API/DDL reference is docs/integrations/contracts-0005;
the historical contracts/v2 export is preserved separately.

## Earlier DR checkpoint at 12:04 UTC

HISa30f is publicly ready on migration04 with DR289/schema1 and LabClearc194,
each receiver using a dedicated database and loopback listener. Fresh production
backup/actual isolated restore verified112 tables/one file. Activation preserved
all original row hashes/files/sessions, all9 committed results,3 selected hashes
and inference9. No production seed or restore occurred.

| Current extension | Executed scope | Remaining limit |
| --- | --- | --- |
| HIS/receiver software | Main77 HIS PostgreSQL,37 receiver, independent2 quality checks; HIS25 unit/135 component/3 audit/build | Does not repeat all38 domains |
| Final DR human-label frontend |522 unique-case composite coverage;521 full-run passes/one native30s timeout, unchanged isolated2 pass; main76 focused/UWF2/typecheck/build | Retain full-run failure; do not call it522 passes in one run |
| Protected public DR manual journey | Native Chrome consent, original640x480 previews, quality/patient/eye confirmation, unsigned draft save/full reload and explicit unsigned check; DB readback | Earlier7c76 rendered acceptance; final34fd label-only browser smoke NOT_RUN after physical Escape stop |
| Final34fd static refresh | PASS12:04:20Z:3 databases/files,59 non-app container IDs and registry bytes/UID10001/0600 preserved;10 authenticated assets matched | Initial pre-dispatch directory failure retained separately; not a new clinical write |
| Public LabClear manual review | Source6 to reviewed7, explicit confirmation, reload/read-only reopen; source unchanged/task open | No live laboratory interface or clinical/model result |
| LabClear authorized source/theme |76 tests and bounded actual-browser checks;18 owner file hashes unchanged | Mobile actual width355, requested390; existing Render deployment not changed |

The current DR source is separate local main d8a2d9b, no remote;191 native
backend hashes remain unchanged. Contracts for04 are separately exported at
[contracts-0004](docs/integrations/contracts-0004/manifest.json):142 paths,
120 modeled tables/121 including Alembic. Historical contracts/v2 remain tied
to their baseline image. Ten owner-renamed MMRDR images remain held for unknown
laterality and untouched. No new model calls or grade/signing grants occurred.
The long goal remains ACTIVE pending final label-only public browser smoke,
the owner-added fictional Thai/coherent clinical demo-data UX extension and
closeout. Future intentional demographic amendments must be recorded as exact
post-preservation row/version exceptions, not unchanged original row hashes.
[Public receipt index](evidence/integrations/public-dr-20261114/receipts.json) and
[current integration checkpoint](docs/integrations/VALIDATION_CHECKPOINT_20261114.md).
Original baseline below retains its own verification date and limits.

## Historical selected UI checkpoint — 14 November 2026

Selected Home/Login, Patient Record and logo are deployed with a wide read-only
Patient panel. Final25 unit/91 component/3 audit cases/typecheck/build: PASS
([frozen receipt](apps/web/evidence/patient-record-panel-scroll-20261114-final/checks.json)).
These component checks use jsdom/authored doubles; no new backend suite or all-domain
baseline is implied. Earlier source reviews and local/browser observations retain
their candidate boundaries in [the release report](docs/RELEASE_PATIENT_PANEL.md).

| Source phase | Executed result | Evidence |
|---|---|---|
| Initial selected UI,76 components | Local browser15 and real-model/human persistence PASS;11623ms,413/133 tokens | [local browser](evidence/research-ui-release/browser-local/browser-acceptance.json) |
| Wide Patient panel,89 components | Local8 observations and public desktop/mobile panel; fresh public document/task→Typhoon→human v2→approve→commit→reload PASS | [local panel](evidence/research-ui-release/patient-panel-local/browser-acceptance.json), [public server readback](evidence/research-ui-release/patient-panel-public/public-workflow-readback.json) |
| Final scroll/focus-only candidate,91 components |214 source/17 assets, app-only activation/preservation, origin7 and Access5 PASS; earlier public result readback16/16 PASS | [binding](evidence/research-ui-release/deployment/scroll-reset/runtime-source-binding.json), [preservation](evidence/research-ui-release/deployment/scroll-reset/postactivation-preservation.json), [readback](evidence/research-ui-release/deployment/scroll-reset/prior-public-workflow-readback.json) |
| Final rendered scroll smoke | NavigationY115.2→0, logoutY2.4→0, Login logo top27.6, signinY0 PASS; parent-observed Chrome | [checkpoint](evidence/research-ui-release/release-checkpoint.json) |
| Final interactive persisted proposal reopening | PASS in subsequent authenticated Chrome inspection: exact final bundle, version2/hash/checklist and disabled edit/approval/commit actions; zero new model calls | [final browser receipt](evidence/research-ui-release/final91-public-reopen/acceptance.json) |

Public run9b797df1-18b5-4537-b036-b37cf8d337ca produced result
64d8a1ae-958c-4c33-a4e8-fa222c1e8448 in11563ms,424input/134outputtokens,costnull.
Readback16 checks include exact source/version binding, action hashes, human v2
approval, canonical commit, replay and one attempt/proposal/result. The final swap
preserved180 preexisting sessions, three selected results, one file and109 table
counts; no restore/seed/account/connector/DB/model change occurred. Backend/AI
sources are unchanged between the public workflow and final scroll-only image.

The overall long goal is ACTIVE. This historical UI phase predates the separate
DR/LabClear integration work described in the current checkpoint above. The38-domain/
10-journey local baseline below was not rerun. This authored synthetic integration
flow does not establish clinical/product effectiveness or throughput.

The13 November deployment/public workflow passed; see the historical triadic section below. Local/pause observations retain their original dates and scope.

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
- NOT_RUN / NOT_CONNECTED: payer/national/HIS/LIS/PACS connectors, production IdP, training, clinical deployment, hospital SOP acceptance and clinical/product effectiveness.
- UNKNOWN: original GGUF Hugging Face revisions, general real-world model quality, engine-side cancellation and live cost. Unknown values remain null.
- The native application launcher alternative was not needed; the Windows Docker app and native disposable PostgreSQL tests were executed.

## Reproduction and release integrity

Follow START_HERE.md. The validation runner accepts --output-dir to preserve earlier evidence. Browser scripts support --help safely and require private HIS_SEED_PASSWORD from the local .env, never a public demo token.

Regenerate contracts with scripts/export_contracts_v2.py, check consistency with scripts/check_fullsystem_package.py, and package reviewed tracked files with scripts/package_release.py. SHA256SUMS.json excludes itself; ZIP CRC and every included source hash are verified. .gitattributes preserves exact bytes across Git checkouts.

Initial checkpoint documents are retained under evidence/fullsystem/windows-20261113/initial-docs/. The dated matrix review remains historical; current coverage and executed evidence control local acceptance.

## Historical frontend refresh and Cloudflare preparation — 13 November 2026

This extension preserves the backend and the historical real-model evidence. The new interface uses the user's yellow/gray/purple/orange palette, self-hosted OFL Thai fonts, compact navigation and progressive details. References are documented in docs/design/REFERENCE_REVIEW.md; no competitor code or assets were copied.

| Executed check | Result | Evidence |
|---|---|---|
| Incoming Claude frontend baseline |25 unit/60 component, audit/typecheck PASS |evidence/frontend-refresh/baseline/ |
| Initial refresh run |Unit/audit/type/build PASS; one obsolete greeting assertion FAIL retained |evidence/frontend-refresh/final-checks/ |
| Final themed frontend |25 unit/63 component, audit/typecheck/build/runtime dependency audit PASS |evidence/frontend-refresh/final-themed/ |
| Cloudflare helper and existing launcher/CLI |16 tests/28subtests PASS, including12 new helper tests |evidence/frontend-refresh/deployment-checks/ |
| Offline ingress + resolved Compose fixture |PASS; private bindings, Securecookie, exactHTTPS origin,90s deadline |deploy/cloudflare/local-readiness.json |
| Themed Docker start |PASS; existing DB migration0002, no seed/reset |evidence/frontend-refresh/docker-themed/ |
| Actual production-browser |13 observations PASS: desktop/mobile, no horizontal page overflow/pageerrors, menuEscape, five recorded findings, disabled historic approval and exact11205ms provenance |evidence/frontend-refresh/production-browser/execution.json |
| Current runtime binding |45 backend/frontend/build/font/license files PASS |evidence/frontend-refresh/production-browser/runtime-binding.json |
| Independent source review |3 findings repaired with component regressions; no remaining actionable blocker in reviewed scope; reviewer didnot independently rerun tests |evidence/frontend-refresh/production-browser/review.json |

No new model inference or domain record mutation was made by this browser refresh test; login/logout and readonly historical result inspection were used. The reported11205ms belongs to the earlier pinned Typhoon run and is not a new latency measurement. The full38/10 baseline and PostgreSQL suites were not rerun for this frontend-only extension.

A local dist comparison first found stale output from before final stylesheet comments; rebuilding local assets produced the exact Docker build hashes. No runtime mismatch remains. The mechanical style scan flagged a2px history divider; it was reduced to1px. Visual confirmation was bounded to preview inspection and final production desktop/mobile checks.

Owner selected his.ai-cie.com and confirmed a Cloudflare account without a Tunnel. Read-only browser inspection found the domain in that account; no account/DNS/security/tunnel settings were modified. Actual owner credentials, Tunnel and Access policy remain pending. This release is locally prepared for that setup; public deployment/external browser remains NOT_RUN. Thai setup/resume steps: docs/CLOUDFLARE_SETUP_TH.md.

## Triadic redesign and protected dr-train deployment — 13 November 2026

This owner-resumed scope supersedes the previous preparation/pause and yellow/gray/purple/orange theme. Exact anchors now #1C4286/#861C42/#42861C. Existing backend runtime code remains unchanged; scoped frontend and new isolated deployment helpers are separately evidenced.

| Executed gate | Observed result |
|---|---|
| Frontend release-checks |25 unit/69 component, audit, typecheck and build PASS |
| Final Escape timing repair |69 component/typecheck/build PASS after repair; frozen source hashes recorded |
| Actual local responsive confirmation |13 observations PASS on loaded desktop1440/tablet1024/mobile390 screens; drawer focus/inert/Escape and persisted live findings; no new inference |
| Hallmark static/login render |0 FAIL/0 REFLEX/2 retained documented WARN; authenticated app inspected separately |
| Independent no-slop review |Six sections PASS; source/regression reports/screenshots reviewed, tests not independently rerun |
| New deployment contract units |3 tests with3 subtests PASS |
| Initial Windows→server copy |109 table counts including Alembic and one file checksum exact; old live result preserved, no source reset |
| Final server replacement |Fresh backup; only app recreated;48 runtime source hashes and21 built assets match reviewed checkout/build; test01 and178 prior sessions preserved |
| Dedicated service placement |App/DB/connector healthy, restart unless-stopped; selected18080/15432/11434/20331 listeners loopback-only;4 connector HA connections observed |
| Public unauthenticated boundary |5/5 HTTPS requests302 to ai-cie.cloudflareaccess.com, including invalid assertion; no token stored |
| Actual public Chrome workflow |11 recorded observations PASS: saved synthetic source, exact Home context, one real AI call, human editv2/approve/commit/reload and completed-task Home update |
| Read-only server workflow receipt |One run/proposal/result; exact source/approval/result hashes and6 audit records; no inference/writes during readback |

Evidence: evidence/triadic-ui/release-checks, final-freeze and confirmation; evidence/triadic-release/independent-ui-review.json; evidence/triadic-release/public-final/browser-acceptance.json and access-boundary.json; evidence/deployment-20261113/final-deployment-verification.json, final-resource-verification.json and public-workflow-readback.json.

Public run63506882-333c-479c-992e-027b991c836a used real dr_train_ollama/Ollama0.12.6 with model manifest ab914ef406c9a78e2a8893eaa3b0ef78049f6c4e2703626433028e838d3a168b. Elapsed10414ms,422 input/136 output tokens, measured_cost null. One authored source yielded4 present/plan missing/0 unclear, all quotes contained in exact saved source. Proposal b6cc13f6-fa9e-4985-96a2-4646e113c180 changed action hash fromv1 tov2 after human edit; test01 approvedv2 and result ef4e9f7e-e0b2-473e-ab55-79ea383ffb72 stores that hash. Reload retained reviewed content and disabled repeated mutation controls.

Private server credentials/session/passwords are excluded. The owner requested the dedicated test01 account; actual login, allowed D22/D37/clinical approval, patient001-only scope, admin403 and other-patient404 were verified. Global account policy and existing users remain unchanged. Public Access allows only the owner's three configured emails; no Bypass observed. Exact recipient addresses are not published.

Retained harness issues: default browser clicks without an explicit mouse button initially did not activate; explicit left-click worked. Required-label/disclosure selectors were corrected using observed roles/AX. Full-page screenshot timed out; normal screenshots were saved after resetting viewport. These issues caused no duplicate domain writes or additional inference. Original local loading-only Home image and initial failed create-label regression remain clearly marked in the UI report. Initial deployment SQL/header probe corrections remain in deployment receipts.

The deployed image is his-poc-server:triadic-778ba97bf46f, IDsha256:6144c7744b6976c8f0c142486acc4baaa283f0515f1d36c3a951337e53773935. Snapshot201files SHA778ba97bf46f714b0b9290555549a6aeab09d5228e279204d28a53a1f8d8f7d4. Documentation/metadata/evidence were reconciled after this runtime snapshot; exact frontend/backend/assets are bound by the48/21 receipt, not an assertion that every later documentation byte is inside the image.

This is one protected synthetic workflow and bounded software deployment, not a full rerun of38 domains/10 journeys, a clinical/semantic benchmark, production certification or throughput/SLA test. Original local L2/L3 evidence is retained. HF revision and engine-side cancellation remain UNKNOWN; MedGemma inference and other external integrations remain NOT_RUN. Windows and server data diverge after the initial copy. A Git push does not automatically deploy.
