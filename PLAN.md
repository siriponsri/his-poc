# Goal-based implementation milestones

## Active long goal and UI checkpoint — 14 November 2026

1. Selected Clinical1 Home/Login + Patient2 workspace + logo3, then wide read-only
   Patient panel and explicit route/auth scroll/focus repair: implemented/deployed.
2. Final frontend25 unit/91 component/3 audit cases/typecheck/build: PASS. Component
   doubles, independent review and actual browser observations remain distinct.
3. Fresh public synthetic document/real-AI/human v2/approval/commit/reload on the
   preceding89-component candidate: PASS. Its16 server readback checks pass again
   after the final UI-only swap; no repeated inference was needed for scroll reset.
4. Active image167d14addf47:214 source/17 asset binding, backup, app-only replacement,
   180 prior sessions/three results/file preservation, origin7 and Access5: PASS.
5. Final rendered navigation/logout/signin scroll smoke: PASS. Interactive reopening
   of the persisted proposal after that last swap: NOT_VERIFIED; investigate via
   the existing authenticated browser when its current URL can be verified.
6. Continue separate CareBalance DR derivative and LabClear integration/theme work.
   These are active future tasks, not delivered integrations in this UI release.

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
