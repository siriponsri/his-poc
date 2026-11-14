# Goal-based implementation milestones

## Latest realistic-patient checkpoint

The long goal is ACTIVE. The production fictional cohort/API batch PASSED: 146 normal mutations once; six new patients/OPD visits/notes, eleven released labs, twelve OPEN reviews (23 total new tasks includes eleven completed acquisition tasks). Four legacy Patient display names changed with audited version1→2; old DOB/sex/HN and every old nonpatient row/file remain. All9 prior inference runs/results remain; DR/LabClear rows and credentials/roles are unchanged.

The independently reviewed UI source5a26ed6 is integrated into main: actual scoped identifiers, completed age, sex and readable visit context. PASS31 unit/139 mounted, typecheck/build; six PostgreSQL privacy cases and an overlapping nine-case scoped regression. The initial outdated Home fixture failure is retained. The live app is still HISa30 on migration04: this new UI is NOT_YET_DEPLOYED at this source checkpoint.

Pending: fresh current04 backup/isolated restore, candidate/rollback qualification, app-only activation, final authenticated rendered UI/DR label and retained workflow checks, then final publication/handoff. Current protected browser displayed all six new names and twelve review tasks on the prior app; this does not establish the new age/HN UI acceptance.

[Authored cohort and evidence](evidence/integrations/realistic-demo-data-20261114/DEMO_DATA.md). Earlier sections below are retained checkpoints with their original states and preservation scope; their NOT_IMPLEMENTED data status predates this completed batch.

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
