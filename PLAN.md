# Goal-based implementation milestones

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
