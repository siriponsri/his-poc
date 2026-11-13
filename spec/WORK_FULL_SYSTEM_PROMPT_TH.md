# คำสั่งให้ Work — ขยาย HIS POC เป็น Full System Development Prototype

วันที่: 12 พฤศจิกายน 2026  
เอกสารนี้ใช้คู่กับ starter v0.2.0 และชุด review/spec ที่แนบมา เป็นคำสั่งสำหรับงานรอบใหม่ ไม่ใช่รายงานว่า implementation ต่อไปนี้เสร็จแล้ว

## วิธีส่งงาน

แนบสองชุด:

1. `HIS_POC_Starter_v0.2.0_2026-11-12.zip`
2. `HIS_POC_Full_System_Review_and_Work_Brief_2026-11-12.zip`

คัดลอกข้อความใต้หัวข้อ “เริ่มคำสั่ง” ไปให้ Work หากอยู่ในแชตเดิม ให้ย้ำว่าขอบเขตใหม่นี้แทนข้อจำกัด singleton/first slice ใน brief เดิม แล้วให้ Work อ่านไฟล์ในชุดใหม่ก่อนลงมือ

---

## เริ่มคำสั่ง

คุณกำลังทำโครงการ HIS POC ต่อจาก `HIS_POC_Starter_v0.2.0_2026-11-12.zip` ให้ลงมือพัฒนารอบใหม่เป็น **Full System Development Prototype** ที่เปิดเว็บแล้วเข้าหน้า login ใช้งานตามบทบาท รองรับหลายผู้ป่วย หลาย encounter และหลาย tasks มีโมดูลทั้ง 38 domains ที่ทำธุรกรรมขั้นต่ำของแต่ละ domain ได้จริงบน PostgreSQL และเชื่อม workflow ข้ามโมดูล

นี่เป็นการเปลี่ยนขอบเขตจาก first slice เดิมอย่างชัดเจน ข้อจำกัด p-demo/e-demo/task-demo และคำสั่งห้ามขยายหลายผู้ป่วยในเอกสารเก่าให้แทนที่ด้วย migration, task binding และ authorization ที่ถูกต้อง อย่าลดเป้าหมายกลับไปเป็น 38 เมนูหรือ placeholder pages และอย่าหยุดเพียงเสนอแผน ให้ทำ implementation, verification และ handoff ต่อเนื่องตาม dependency ที่พร้อม

### A. อ่านและยืนยัน baseline

อ่าน starter instructions และเอกสารต่อไปนี้ก่อนเปลี่ยน code:

- `START_HERE.md`, `AGENTS.md`, `GOAL.md`, `PLAN.md`, `BACKLOG.md`, `CODEX_HANDOFF.md`, `VALIDATION_REPORT.md`, `DECISIONS.md` และ contracts ของ starter
- `REVIEW_V020_TH.md`
- `FULL_SYSTEM_SPEC_TH.md`
- `DOMAIN_IMPLEMENTATION_MATRIX.md` และ JSON คู่กัน
- `POSTGRESQL_DECISION_AND_MIGRATION_TH.md`
- `ACCEPTANCE_TEST_PLAN_TH.md`

ตรวจไฟล์จริงและรัน baseline ที่ environment รองรับ เก็บผลตามจริง หากคำสั่งเดิมรันไม่ได้ให้ระบุเหตุผล ไม่คัดลอกผล PASS ของผู้สร้างมาเป็นผลรันของคุณ รักษาต้นฉบับและทำงานในรุ่น/branch ใหม่ โดยไม่ทับข้อมูลหรือไฟล์ที่ผู้ใช้แก้เอง

รอบ review พบ 45 backend tests, 17 React adapter/helper tests, 12 legacy UI tests ผ่าน รวม contracts 23 schemas/176 parity cases/27 fresh HTTP responses แต่ไม่มี browser assertions และยังไม่มี PostgreSQL implementation ตัวเลขเหล่านี้ไม่ใช่หลักฐานว่า full application เสร็จแล้ว

### B. แก้ frontend findings ก่อนใช้ pattern เดิมขยายหลายโมดูล

1. F20-01: mutation สำเร็จแต่ refresh ล้มเหลวต้องไม่ทำให้ proposal ที่แสดงกับ review/action binding เป็นคนละ revision ใช้ response อัปเดต record อย่างสอดคล้อง หรือปิด action จน reconcile สำเร็จ
2. F20-02: แยก definitive rejection เช่น stale/conflict ที่ contract รับรองว่าไม่เขียน ออกจาก unknown commit outcome; ให้ผู้ใช้ recover ต่อได้โดยไม่ reconnect เพื่อทิ้ง state
3. F20-03: เมื่ออ่านกลับพบผลที่ตรง operation/proposal/version ให้ reconcile pending และแสดง confirmed result ใช้ identity ที่ตรวจสอบได้ ไม่ใช้เพียง HTTP 200
4. F20-04: แยก skip-link/focus behavior จาก application routing และมี not-found route

เก็บ reproducer เดิมเป็นหลักฐานก่อนแก้ แล้วเพิ่ม regression tests ที่ยืนยันพฤติกรรมหลังแก้จริง ตัว reproducer ที่พบ bug ได้ exit 0 ไม่ใช่ acceptance PASS

### C. สถาปัตยกรรมที่ให้ใช้

- Frontend: รักษา React + TypeScript + Vite จาก v0.2 ปรับ routing/authentication/shared state และเติม domain screens ใช้ component system หลักชุดเดียว รักษา license/provenance ของ template
- Backend: FastAPI modular monolith แยก modules/services/repositories/contracts ชัดเจน ไม่แยกเป็น 38 microservices
- Database: **PostgreSQL 18.x ที่รองรับ** เป็นฐานหลัก ตรวจ minor และ compatibility ของ dependency ตอนเริ่ม แล้ว pin รุ่นจริง ใช้ SQLAlchemy + PostgreSQL driver ที่รองรับ + Alembic migrations
- Authentication: server-verified local development accounts, password hashing library, server-backed sessions, effective role/permission/scope read model; เตรียม boundary สำหรับ OIDC ภายหลัง
- File storage: interface สำหรับ local development files และ object storage ภายหลัง เก็บ reference/checksum/version/authorization metadata ใน PostgreSQL
- AI: shared gateway รองรับ mock, cloud API, server/dr-train และ local adapters แบบ configuration ที่ชัดเจน เปิด explicit mock เป็น default; ยังไม่เปิด live routes ที่ endpoint/model revision ไม่ทราบ
- Jobs/integration: durable status/retry/outbox เมื่อ workflow ต้องใช้ โดยไม่มีการถือ database transaction ค้างระหว่างเรียกโมเดลหรือระบบภายนอก

Supabase เป็นทางเลือกของ platform ที่ใช้ PostgreSQL ไม่เป็นข้อบังคับให้สมัครบริการก่อนเริ่ม ใช้ SQLite เดิมเฉพาะ legacy regression/import tooling ที่ระบุชัด ห้าม fallback เป็น SQLite แล้วรายงานว่า PostgreSQL ผ่าน

### D. ประสบการณ์เข้าใช้งานที่ต้องครบ

เปิด root URL → ถ้าไม่มี session ให้เข้า `/login` → backend ตรวจบัญชี → โหลด current user/permissions → เข้า home/worklist ตามบทบาท

ต้องมี logout, expiry/revocation, deep-link refresh, access denied, not found, network failure และการล้างข้อมูลของผู้ใช้เดิมเมื่อเปลี่ยน session การเลือก role/context ใช้เฉพาะ memberships ที่ server ยืนยัน ไม่ใช้ dropdown เปลี่ยนสิทธิเอง

ให้มีบทบาทขั้นต่ำตาม spec: registration, clinician, nurse, laboratory, imaging, pharmacist, billing/claims, finance, inventory/procurement, quality/analyst, system admin, auditor และ patient portal user แยก system administration ออกจากสิทธิรับรองงาน clinical

หน้า home ต้องแสดงงานและตัวเลขจากข้อมูลจริงที่ผู้ใช้มีสิทธิ พร้อม link ไปต้นทาง จัด sidebar เป็นกลุ่มงานและค้นหาได้ ใช้ shared patient/encounter header ในงาน clinical ส่วน patient portal มี shell และ scope ของตนเอง

### E. ทั้ง 38 domains ต้องมีความสามารถขั้นต่ำที่ทำงานได้

ใช้ `DOMAIN_IMPLEMENTATION_MATRIX` เป็นขอบเขตบังคับราย D01–D38 ทุก domain ต้องมีรายการ/ค้นหา/รายละเอียด/ฟอร์มหรือ actions ที่เหมาะกับงาน, state transitions ที่ backend ตรวจ, PostgreSQL persistence, references ไป shared entities, history/audit และ acceptance evidence

เป้าหมายคือ **D01–D38 ถึง L2** และ **J01–J10 ถึง L3** ตามนิยามใน spec แยก `implementation_status`, `verified_level`, `verification_status` และ `external_integration_status` ออกจากกัน NOT_RUN เป็นผล verification ไม่ใช่หลักฐานว่า implementation อยู่ระดับใด

ใช้ shared components ได้ แต่ generic JSON editor, generic task CRUD, route ที่แสดงข้อความ “planned” หรือจำนวน schemas ไม่ถือว่าทำ workflow ของ domain นั้นเสร็จแล้ว Domain ที่ไม่มี external endpoint ยังต้องทำ local manual/synthetic workflow ตาม matrix ให้เดินได้ เช่น รับ specimen และลงผลเอง, รับภาพและลงรายงานเอง, บันทึก remittance สังเคราะห์ หรือสร้าง referral document

งานที่ต้องใช้กฎ clinical เฉพาะ ให้ทำ documentation, scheduling, manual verification และ human authorization ตาม matrix อย่าสร้าง automatic diagnosis/dose/triage/blood compatibility หรือการลงนามที่อ้างผ่านข้อกำหนดจริงจาก field/status เพียงอย่างเดียว

### F. Shared data และ migration

เพิ่ม organization/facility/department/location, users/memberships/roles/permissions/sessions, patients/identifiers, encounters/admissions, tasks, immutable document revisions, orders/results, prescriptions/dispensing, stock movements และ financial records ที่อ้าง shared IDs

ใช้ relational constraints สำหรับความสัมพันธ์และความถูกต้องที่สำคัญ กำหนด uniqueness ตาม scope, index ตาม query, money/quantity precision, timestamp/time zone และ state/version fields อย่างชัดเจน JSONB ใช้กับ extensions/payloads ที่เหมาะสม ไม่ใช้แทนทั้ง schema

Migration ต้องรักษา legacy IDs หรือมี mapping ที่ตรวจได้ รักษา canonicalization/hash/version/idempotency และ audit relationships ของ first slice เดิม ตรวจว่า JSONB representation ไม่ทำให้ hash ที่อนุมัติไว้เปลี่ยนโดยไม่ตั้งใจ

หาก legacy SQLite ไม่เหลือข้อความ revision เก่าที่ถูก overwrite แล้ว ให้รักษา IDs/mapping, original hash, approvals/results และ audit เป็น read-only legacy evidence unavailable หรือ quarantine พร้อมรายงาน gap ห้ามแทนข้อความเก่าด้วย current text สร้างเนื้อหาย้อนหลัง หรือเปลี่ยน hash เพื่อให้ import ผ่าน ห้าม new commit บน proposal ที่ขาด required evidence revision; การอ่าน/replay ผลที่ commit แล้วต้องตรวจสิทธิและไม่สร้าง write ใหม่ แยก acceptance ของ legacy ที่ขาดต้นฉบับจากข้อมูลใหม่ที่ต้องมี immutable history ครบ

Seed ต้องมีหลายผู้ป่วย/encounters/tasks และทุกบทบาท รวมข้อมูลข้าม scope สำหรับ negative tests ทำซ้ำได้โดยไม่ duplicate และแยกจาก startup อย่านับ 18 UI scenarios เดิมว่าเป็น backend patients

เรื่อง open data ให้เก็บ source/rights/version/checksum/mapping/import report ของข้อมูลที่นำมาใช้จริง หากยังไม่ได้ดาวน์โหลดหรือ import ให้ระบุสถานะนั้น ใช้ deterministic synthetic data ทำให้ทุก local workflow รันได้ก่อน และทำ ingestion ของชุดข้อมูลเปิดที่เข้าถึงได้/มีสิทธิชัดเจนเป็นงานแยก ห้ามนำ real patient data หรือไฟล์ที่ยังไม่ทราบสิทธิมา bundle

### G. API และการเชื่อม frontend

กำหนดเจ้าของ contracts กลาง ใช้ typed DTO และ versioned API สำหรับ auth/me/patients/encounters/tasks และ domain capabilities การเปลี่ยนจาก v1 stringified JSON fields ต้องมี v2/compatibility plan ห้ามเปลี่ยน wire contract ใต้ route เดิมโดยไม่ทดสอบผู้เรียกเดิม

หากคง `/api/v1` ให้รักษาเฉพาะ DTO/wire compatibility โดยใช้ session/permissions/scope middleware ชุดเดียวกับ API ใหม่ ประกาศ auth migration และปฏิเสธ public demo bearer tokens เดิมใน default application profile การรัน legacy token tests ต้องอยู่ isolated legacy profile ที่ปิดโดย default แยกฐานข้อมูลและ listener ไม่ mount token handler เดิมเป็นทางเข้าข้าง login/session ใหม่

Backend ต้องตรวจสิทธิของ read/write/export/action ทุกครั้ง ไม่เชื่อ patient/role ที่ client ส่งมา ต้องป้องกันผล query หรือ draft ของผู้ใช้/ผู้ป่วยก่อนหน้าค้างเมื่อสลับ context

Financial flows ต้องแยก billed, submitted, approved, gross_received, refunded, net_received, outstanding และ cost โดย net_received = gross_received − refunded ไม่เขียนทับ gross receipt เดิมเป็นยอดสุทธิ ส่วน outstanding อิง invoice adjustments/payment allocations ตาม policy ไม่อนุมานจาก refund เพียงรายการเดียว Stock/dispensing/receipt/refund/reversal ใช้ transaction และ unique/idempotency constraints ที่เหมาะสม การ retry ต้องไม่จ่ายยา ลด stock รับเงิน คืนเงิน หรือออกผลซ้ำ

### H. Local run ที่ผู้ใช้เปิดได้

ส่ง Docker Compose พร้อม health/readiness และ persistent development volume รวม PowerShell launcher ที่ตรวจ Docker engine/Compose/environment ก่อนรัน Default publish เฉพาะ web entrypoint บน `127.0.0.1` ให้ฐานข้อมูล/backend อยู่ internal network โดยไม่มี published host ports; debug ports เปิดเฉพาะ explicit profile และ bind `127.0.0.1` หากผู้ใช้เลือก native PostgreSQL ผ่าน `DATABASE_URL` ให้มีขั้นตอนที่รองรับชัดเจน

มีคำสั่ง migrate, seed, start, stop, logs, backup และ restore ไปฐานทดสอบใหม่ โดย start/restart ไม่ลบข้อมูลหรือ seed ทับ edits Backend connection string/secrets ต้องไม่เข้า frontend bundle

ลำดับเริ่มครั้งแรกต้องเป็น DB readiness → explicit migration → explicit seed → application startup/readiness; seed ทำเมื่อเลือกคำสั่งหรือ flag ชัดเจนเท่านั้น ไม่ทำทุก restart ใช้ timeout และหยุดเมื่อ migration ล้มเหลว ห้ามรอ application readiness ก่อน migrate หรือ seed ต่อหลัง migration fail เส้นทาง native PostgreSQL ใช้ลำดับเดียวกัน

หลังเริ่มระบบให้เปิด URL เดียวแล้วพบ login ต้องทำงานทั้ง dev และ production build ที่ตั้งค่า same-origin API/deep-link routing จริง ไม่สำเร็จเฉพาะผ่าน Vite dev proxy

หาก runtime ไม่มี Docker/PostgreSQL/browser ให้ทำ source/schema/contracts/tests/scripts ที่ไม่ติด dependency ต่อ บันทึกงานที่ยังรันไม่ได้และคำสั่งให้ผู้รับช่วง ห้ามประกาศผ่าน full-system acceptance ถ้าเงื่อนไขสำคัญยัง NOT_RUN

### I. ลำดับทำงานและการแบ่ง agent

1. F0: baseline + audit fixes + เปลี่ยน scope เอกสารให้ตรง full system
2. F1: PostgreSQL/migrations/auth/shared patient-encounter-task-document core
3. F2: role workspaces และ functional minimum ทั้ง 38 domains ตาม matrix
4. F3: เชื่อม J01–J10 ด้วยข้อมูลและสิทธิชุดเดียวกัน
5. F4: PostgreSQL integration/concurrency/restore, browser workflows และ clean install/run
6. F5: release, coverage/evidence, runbooks และ Codex handoff

แบ่งงานขนานตามกลุ่ม domain ได้หลัง contract/schema owner กำหนด shared interfaces แบ่ง ownership ไฟล์ชัดเจนและมี integrator ตรวจ migrations/API/nav/data ให้ตรงกัน อย่าให้หลาย agents สร้าง patient/user/encounter table หรือ authentication ซ้ำคนละชุด

Checkpoint เป็นจุดบันทึกงาน ไม่ใช่เหตุให้หยุดลด scope ถ้ายังทำต่อได้ ให้เดินต่อจนถึงเป้าหมาย ถ้าถูกจำกัดจริง ให้ส่ง repo ที่ต่อได้พร้อม coverage ราย domain และ blocker ที่เฉพาะเจาะจง ไม่เปลี่ยนชื่อ placeholder release เป็น full system

### J. สิ่งที่ต้องส่งมอบ

- Source ที่เปิดใช้งานได้พร้อม dependency locks และ release manifest
- Login/session/RBAC, role homes, patient/encounter selection และหน้าทำงานทั้ง 38 domains ตาม matrix
- PostgreSQL schema/migrations, SQLite import/mapping ที่ระบุขอบเขต, deterministic seeds และ ERD/data dictionary
- OpenAPI/contracts พร้อม runtime validation และ typed client ที่เชื่อมหน้าจอจริง
- Compose/PowerShell/native run instructions, `.env.example`, backup/restore และ upgrade notes
- `DOMAIN_COVERAGE.md`/JSON: ต่อ domain ระบุ route, service, tables, transitions, tests, `implementation_status`, `verified_level`, `verification_status`, `external_integration_status` และข้อจำกัด
- `JOURNEY_COVERAGE.md`: J01–J10 พร้อม record IDs/actors/evidence ของรอบรันจริง
- `VALIDATION_REPORT.md`: แยก legacy, PostgreSQL, component, browser, build, clinical/product/live inference; ระบุ PASS/FAIL/NOT_RUN ตามจริง
- Updated `AGENTS.md`, `GOAL.md`, `PLAN.md`, `BACKLOG.md`, `DECISIONS.md`, `START_HERE.md`, `CODEX_HANDOFF.md` และ prompts ที่ไม่ขัดกัน
- Data/template/license provenance และรายการสิ่งที่ไม่ได้ bundle/import

หากหลักฐานครบจึงเรียกผลว่า full-system development prototype ที่ผ่านเกณฑ์ตาม scope หากยังไม่ครบให้เรียก checkpoint พร้อมระบุส่วนที่ค้าง ทุกส่วนต้องอยู่ใน repo/ไฟล์ส่งมอบ ไม่ให้คำอธิบายในแชตทดแทน implementation

เริ่มจากอ่าน baseline แล้วลงมือได้เลย ใช้การตัดสินใจในชุดแนบเป็นค่าเริ่มต้น ไม่ต้องรอ API keys, dr-train endpoint, exact model revision หรือ deployment cloud เพื่อสร้างระบบภายในนี้

## จบคำสั่ง
