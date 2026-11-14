# HIS POC — Full System development target

## Active owner extension — 14 November 2026

Latest DR gate: HIS77, receiver37 plus2 independent quality-guard checks, and
the prior complete DR frontend514 qualification pass. Private Linux workflow,
same-DB rollback and the manual-quality image upgrade pass. The coordinator
executed the private browser draft/reload, limited-permission, mobile390 and
exact-return journey; a final small frontend UX refinement is being qualified.
Fresh production backup/restore, public DR activation, main integration and
protected public DR acceptance remain open. Existing public LabClear remains
active on migration03. Ten owner-renamed MMRDR images are held for laterality;
no new model call or grade/signing grant. See [DR release checkpoint](docs/integrations/DR_RELEASE_20261114.md).

The long goal remains ACTIVE: improve the patient reading journey, create a
separate CareBalance derivative based on dr-support-screening-poc while preserving
the original project, and connect LabClear with authorized source/theme changes.
The LabClear gateway/isolated receiver and actual private browser round trip are
qualified; the current HIS frontend passes25 unit/135 component/3 audit cases
and build. Separate DR theme main and the bounded manual receiver are qualified
within the explicitly recorded software/private-runtime scope.
LabClear activation and authenticated public synthetic journey now pass. DR
integration acceptance remains ongoing. See the [integration checkpoint](docs/integrations/VALIDATION_CHECKPOINT_20261114.md).

## Historical selected UI qualification

The selected Clinical Workspace Home/Login, Patient Record workspace, Operations
Desk logo and wide read-only Patient panel are deployed. Final25 unit/91 component/
3 audit cases/typecheck/build pass. Active image167d14addf47 matches214 source files
and17 assets; backup and app-only replacement preserved180 prior sessions, three
selected results and the stored file. Seven origin hashes and five Access gates pass.

The preceding89-component candidate passed a fresh public synthetic
Typhoon→human v2→approve→commit→reload workflow. Its exact result passes16 read-only
checks again on the final scroll/focus-only image. Final rendered navigation/Login
scroll smoke passes; final interactive persisted-proposal reopening subsequently passed in Chrome
with exact version2/hash/checklist and disabled mutations (zero new inference).
See [current checkpoint](docs/RELEASE_PATIENT_PANEL.md) and
[user journey](docs/USER_JOURNEY_TH.md). Do not mark the full long goal complete.
Earlier completed milestones below retain their original acceptance scope.

เป้าหมายรอบนี้แทนข้อจำกัด singleton ของ v0.2 โดยชัดเจน: แอป HIS/ERP ที่ login จริง ใช้ PostgreSQL เป็นฐานหลัก มีหลายผู้ป่วย/encounters/tasks และใช้ identity, scope, evidence และ audit ร่วมกันทั้งระบบ สำหรับ solo owner และ synthetic development data

เกณฑ์รับเป้าหมาย: D01–D38 ถึง L2 และ J01–J10 ถึง L3 ตาม `spec/DOMAIN_IMPLEMENTATION_MATRIX.json` และ `spec/ACCEPTANCE_TEST_PLAN_TH.md`. L2 ต้องมี workflow ของ domain นั้นพร้อม PostgreSQL persistence และ evidence; L3 ต้องมี integration/browser evidence ของ journey. เมนู ฟอร์ม schema หรือ tests ของ SQLite ไม่ทดแทนเกณฑ์เหล่านี้

สถานะที่ทำจริงแยกอยู่ `DOMAIN_COVERAGE.json`, `JOURNEY_COVERAGE.md`, `VALIDATION_REPORT.md`. ถ้าส่วนสำคัญยังไม่ผ่าน ผลส่งมอบต้องเรียก checkpoint ไม่ประกาศ full-system acceptance. ไม่ลด target เพื่อให้รายงานผ่าน

ระบบประกอบด้วย React/TypeScript/Vite, FastAPI modular monolith, SQLAlchemy/Alembic, PostgreSQL18, server-backed local development sessions และ domain services. ส่วน application location แยก inference location. AI default เป็น explicit mock; dr-train เปิดได้เฉพาะ profile document_review บนข้อมูลสังเคราะห์ที่ผู้ใช้อนุญาตและตรวจ engine/model digest แล้ว ส่วน cloud/local อื่นยังไม่เปิด

Champion candidates ยังคง 4 งาน: document completeness/review, DR screening/referral workflow, claim completeness/reconciliation และ CAD specialist review. Shared clinical workflow รองรับ manual documentation/authorization; ไม่มี automatic diagnosis/dose/triage/blood compatibility ที่อ้างผ่าน clinical validation

ผลผลิตที่ต้องการคือเจ้าของเปิด URL เดียวพบ login เลือกผู้ป่วยและ encounter ทำงานข้ามหน่วยงาน แล้ว reload/restart ยังพบผลเดิม. เงินรับและต้นทุนสะท้อน ledger จริง แยก billed/submitted/approved/gross_received/refunded/net_received/outstanding/cost. การเชื่อม endpoint ผ่านไม่ใช่ clinical/product effectiveness

ยืนยันแล้วเฉพาะ dr-train Ollama0.12.6 และ Typhoon2.1-Gemma3-12B ที่ผูก manifest digest สำหรับ document completeness; GPU V10032GB และ RTX2080Ti11GB ตรวจพบจริง ส่วน UNKNOWN ยังรวมโรงพยาบาล/SOPจริง, production IdP/clinical deployment, external hospital interfaces, Qwen checkpoint, Hugging Face revision ของ GGUF ที่มีอยู่, paid budget และ intended clinical use. สิ่งเหล่านี้บล็อกเฉพาะงานที่ต้องใช้ ไม่บล็อก local synthetic implementation

## Completed owner extension — 13 November 2026

เจ้าของเปลี่ยนโจทย์เป็น UX/UI ใหม่ตาม no-slop-ui/Hallmark และสามสี #1C4286 / #861C42 / #42861C พร้อมอนุญาต deploy ระบบสังเคราะห์บน dr-train ผ่าน his.ai-cie.com แล้ว งานนี้เสร็จตามขอบเขต: frontend25unit/69component และตรวจdesktop/tablet/mobile13ข้อผ่าน; imageที่ขึ้นจริงผูก source48ไฟล์/build21assetsตรงกัน; สำรองและคัดลอกDB109ตาราง/หนึ่งไฟล์เข้าสภาพแวดล้อมแยก; Tunnel/Access/DNSทำงาน; บัญชีtest01แบบจำกัดสิทธิ์ล็อกอินได้; งานเอกสาร→AIจริง→แก้v2→อนุมัติ→commit→reloadผ่าน URL จริง

หลักฐานล่าสุด: evidence/triadic-release/public-final/browser-acceptance.json และ evidence/deployment-20261113/public-workflow-readback.json วิธีดูแล: docs/DEPLOY_DR_TRAIN.md ข้อมูล Windows เดิมยังอยู่แยกกัน การส่ง sourceเข้า mainไม่ได้ deployอัตโนมัติ งานเชื่อมภายนอกอื่น/clinical/product evaluationยังไม่อยู่ในผลผ่านนี้
