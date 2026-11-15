# Plan — illustrated User Guide release checkpoint

## Active goal — AI evidence, team queue and Admin AI monitoring

Owner-authorized 15 November 2026. Status: DEPLOYED_ACCEPTANCE_IN_PROGRESS.
Runtime source1960a82 / image dfaad737 / schema0006 is deployed on dr-train.
Local qualification and preservation migration passed; new bounded model
and protected-browser acceptance are in progress. Cloudflare Access renewal
is pending for the browser session. No final acceptance or publication of
this milestone is claimed. Baseline c47868a remains the published release.
Copy-only follow-up d8755d9 is locally checked and not yet deployed.
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

Owner-added six-patient fictional-data/metadata and UI task: audit the existing
seed patients, then use normal
versioned/audited APIs for realistic fictional Thai names, DOB/sex and coherent
demo visits/documents/labs. Keep existing HN/identifiers immutable; a new HN
requires a normal new-patient creation. Record each intentional patient-row
version change after the preservation baseline, then verify live names and
retained fixed DR IDs/pseudonym/source snapshots, existing AI results, source
files and permission scope. Normal PATCH support was investigated; actual
dataset/UI implementation, amendment and UX qualification are NOT_RUN.

Current DR gate: source/main qualification, private workflow/rollback, fresh
112-table/one-file backup/isolated restore and public04 activation pass. Actual
protected native-Chrome manual quality/context confirmation, unsigned draft
save/full reload and PostgreSQL readback pass on the preceding7c76 bundle.
Final human-label bundle34fd static refresh/post-refresh preservation pass:
3 databases/files,59 non-app container IDs and registry bytes preserved;
10 authenticated assets verified. Retain the initial pre-dispatch directory
failure and separate successful v2. Final label-only public browser smoke is
NOT_RUN after the physical Escape stop;
fictional-data UX qualification and final publication remain required.
[Public receipt index](evidence/integrations/public-dr-20261114/receipts.json).
Preserve existing LabClear, all9 committed results, inference9 and source files.
[Checkpoint](docs/integrations/DR_RELEASE_20261114.md).

1. Selected Clinical1 Home/Login + Patient2 workspace + logo3, then wide read-only
   Patient panel and explicit route/auth scroll/focus repair: implemented/deployed.
2. Final frontend25 unit/91 component/3 audit cases/typecheck/build: PASS. Component
   doubles, independent review and actual browser observations remain distinct.
3. Fresh public synthetic document/real-AI/human v2/approval/commit/reload on the
   preceding89-component candidate: PASS. Its16 server readback checks pass again
   after the final UI-only swap; no repeated inference was needed for scroll reset.
4. Previous selected UI image167d14addf47:214 source/17 asset binding, backup, app-only replacement,
   180 prior sessions/three results/file preservation, origin7 and Access5: PASS.
5. Final rendered navigation/logout/signin scroll and authenticated persisted
   proposal reopening: PASS, exact version2/hash/checklist, zero new inference.
6. LabClear scoped gateway, isolated receiver and private two-DB/browser journey:
   PASS at the bounded [integration checkpoint](docs/integrations/VALIDATION_CHECKPOINT_20261114.md). Final25/117/3
   frontend checks/build pass. Final5328 public activation and authenticated
   source6 to reviewed7, refresh/read-only reopen/mobile journey now pass.
7. Fixed source-set/manual receiver: HIS77, receiver37 plus2 independent quality
   checks, current HIS25/135/3 and actual protected public synthetic manual
   journey/readback pass. DR final522 unique-case composite coverage retains
   the native timeout/rerun distinction; main76 focused/UWF2/typecheck/build pass.
   Final34fd static/preservation PASS; label-only public smoke, fictional-data
   UX and final docs publication ACTIVE.
   No original DR mutation, live retinal inference or owner MMRDR transfer.

See [release phases and limits](docs/RELEASE_PATIENT_PANEL.md) and
[user journey](docs/USER_JOURNEY_TH.md). These checks do not rerun the original
38-domain/10-journey baseline below. Overall long goal remains ACTIVE.

ขอบเขต F0–F5 แทน M0–M6/B00R–B06R ของรุ่นก่อน. สถานะเป็น evidence-based ใน VALIDATION_REPORT และ coverage; checkpoint เป็นจุดบันทึก ไม่ใช่ข้ออ้างหยุดงานที่พร้อม

| Milestone | ผลลัพธ์ | เงื่อนไขรับ |
|---|---|---|
| F0 | อ่าน baseline/spec, reproduce และแก้ F20-01–04, เปลี่ยน scope เอกสาร | retain original evidence + regression of actual state orchestration |
| F1 | PG migrations/auth/core/shared immutable evidence | migration/seed แยก, sessions/scope/csrf, multi-patient/task PG tests |
| F2 | domain-specific screens/services ทั้ง38 | matrix minimum, valid/invalid transition, scope, audit, persistence |
| F3 | J01–J10 ข้ามโมดูล | shared record IDs, actors, versions, transactions, retry และ evidence |
| F4 | PG concurrency, legacy import, restore, browser/clean run | executed assertions; NOT_RUN เฉพาะ dependency ที่ไม่มีจริง |
| F5 | contracts/config/docs/coverage/release | reconcile contradictions, reproducible commands, hash manifest และ starter prompt |

หนึ่ง core/schema owner และหนึ่ง integrator. งาน UI, clinical modules, ERP modules, operations และ independent review แยก ownership. ไม่สร้าง user/patient table ซ้ำ. API ใหม่ `/api/v2`; v1 token demo อยู่ isolated legacy regression เท่านั้น ไม่ mount ใน default app

ลำดับเริ่มระบบ: DB readiness → migration → seed เมื่อเลือกชัด → app readiness. Native PG และ Compose ใช้กติกาเดียวกัน. ไม่ fallback SQLite. ไม่ reset data ใน startup

หลัง local acceptance จึงเดิน L4 ทีละ named adapter และ evaluator แยกตาม task. Paid API/training/deployment/server changes ต้องมี authorization ของทรัพยากรนั้นจริง ไม่อนุมานจากคำสั่งให้เขียนระบบ

## Executed local gate — 13 November 2026

F0–F4 local synthetic acceptance passed, including38 L2 domains,10 L3 journeys and actual same-app backup/isolated restore. F5 evidence/contracts/coverage are reconciled; release integrity is checked by scripts/package_release.py and scripts/verify_hashes.py. Source publication to the user's main branch is authorized. A subsequent named dr-train document-completeness route has separate actual synthetic inference/browser evidence; it does not rerun or promote all domains to L4. Clinical/production evaluation remains NOT_RUN. See VALIDATION_REPORT.md for multi-run/source binding and retained failures.

## Named live document route — 13 November 2026

Discover existing service/model digests → strict native Ollama adapter → transaction-free reservation/inference/final authorization checks → source-quoted five-item checklist → human edit/approve/commit. Completed: 3 real authored Thai cases, browser PASS7 and readback PASS2, 17 PostgreSQL orchestration tests with injected providers, mock core18 regression, provider/tunnel units and frontend checks. Default remains explicit mock; local private .env opts into the real route. See docs/DR_TRAIN_AI.md and the named evidence section in VALIDATION_REPORT.md.

## Historical frontend and named-host preparation

Refine existing server-backed workspaces in the owner's purple/yellow/gray/orange palette, preserve Claude's incoming work and validate current browser behavior. This local phase passed with separate evidence under evidence/frontend-refresh. Prepare one-origin Cloudflare Tunnel to his.ai-cie.com with Access and private model/DB placement. Owner setup is pending; the user requested a pause with a manual guide before resuming public deployment work.

## Completed triadic redesign and protected deployment

Owner-resumed scope supersedes the previous palette and pause: inspect the supplied no-slop-ui/Hallmark references → redesign actual task/record/review surfaces →25 unit/69 component/audit/type/build → independent review and13 actual responsive observations → frozen source snapshot → backup and isolated dr-train image replacement → Access boundary and real HTTPS document/AI/edit/approval/commit/reload. All named gates PASS. See docs/RELEASE_TRIADIC_DEPLOYMENT.md; full-system local baseline remains separate from this one public workflow.
