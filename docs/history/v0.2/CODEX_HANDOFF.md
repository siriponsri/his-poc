# Codex handoff — HIS POC v0.2.0

ใช้ STARTER_PROMPT_TH.md เป็น prompt รับช่วง และ START_HERE.md เป็นคำสั่งรัน. Read AGENTS, VALIDATION_REPORT, API_IMPLEMENTATION, AUDIT_RESOLUTION และ BACKLOG ก่อนแก้. ตรวจ repository/branch/HEAD/local changes จริงเมื่อวางชุดนี้ลง repo; preserve unrelated work.

## Architecture ที่มีจริง

Backend Python stdlib HTTP + SQLite มี strict request validation และ atomic workflow. Frontend React/TypeScript/Vite อยู่ apps/web มี typed HTTP adapter แยก read-only fixture state; legacy web ยังคงเป็น reference. Provider เป็น explicit mock เท่านั้น. Deployment location แยก inference location โดย live adapters ยัง fail closed.

- Runtime IDs: p-demo/e-demo/task-demo เท่านั้น. Metadata/records หลายรายการใน data ไม่ใช่ backend patient import
- v1 wire contracts: JSON-string columns ใน context/proposal ต้อง parse จุดเดียว; immediate commit result.action เป็น object
- API contract revision 1.0.1 ยังใช้ namespace /api/v1; 23 schema definitions และ canonical workflow fixture ใน contracts/v1/fixtures/workflow.json
- Migration เพิ่ม abstain_reason; ดู docs/MIGRATIONS. Task completed/cancelled/deleted ไม่ reopen เมื่อ restart
- Cloud/model/server resources ไม่มีข้อมูลยืนยันและไม่ได้ถูกเปิดใช้

## Command groups

Package root: `python -m unittest discover -s tests -v`, `node --test tests/test_frontend_behavior.js`, `python contracts/check_contracts.py`, `python scripts/check_data.py`, `python scripts/check_package.py`.

apps/web: `npm ci`, `npm run typecheck`, `npm test`, `npm run build`, `npm run dev`. Vite localhost5173 proxy เฉพาะ /api/v1 และ /health ไป backend loopback8080 (HIS_PORT override ในสอง shells). npm preview ไม่มี backend dev proxy. Optional browser checks/commands และสถานะดู frontend README และ VALIDATION_REPORT.

## เริ่ม coding ที่ไหน

B00R ทำซ้ำ current baseline และ browser journey บนเครื่อง Codex. จากนั้น B01R ย้าย HTTP boundary ไป Python framework ที่เลือก/pin แล้ว โดยคง service/transaction semantics และ request/response parity. ไม่ต้องเขียน UI ใหม่หรือรอ Claude Code.

ต่อด้วย B02R actor/permission read model และ B03R persisted proposal-task binding/migrations ก่อน multi-patient runtime. ห้ามแก้ fixture viewer ให้เขียน API ของ p-demo เมื่อเลือก patient fixture อื่น. การเปลี่ยน identity/session ต้องล้าง state และทดสอบ access revoke/cross scope.

## ขอบเขตของผลตรวจ

ผลจริงและจำนวน tests อยู่ VALIDATION_REPORT; code/build/schema/DOM tests ไม่แทน browser QA. สิ่งที่ NOT_RUN ห้ามยกเป็น PASS. Synthea source ถูกสำรวจ แต่ไม่มี downloaded/bundled dataset เพราะยังไม่ยืนยัน artifact terms; ทำ fixture/mapping ต่อได้. Data fixtures และ model mock ไม่มีน้ำหนักเป็น clinical/business evidence.

## Definition of done

Implement + relevant tests + updated contracts/config/docs/fixtures/provenance + exact command/exit evidence. Failed/timeout/abstained outcomes รวมใน denominator. Paid API/training/deploy/server changes ต้องมี scoped authorization จริง. ถ้างานอิสระพร้อมและอยู่ใน scope ให้ทำต่อ; ถาม owner เฉพาะข้อมูลที่เปลี่ยนทิศทางหรือใช้ทรัพยากรจริง.
