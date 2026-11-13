# Decision log

| ID | การตัดสินใจ | เหตุผล / เงื่อนไขทบทวน |
|---|---|---|
| ADR-001 | เริ่ม isolated starter ไม่เขียนทับระบบเดิม | PharmaCore repo/branch/dirty state UNKNOWN. ตรวจ LabClear main 86ba619bcf481ceae214a067a37513ae9c824bca พบ FastAPI/Jinja/vanilla JS และ SQLite/Postgres; candidate reuse patterns ตาม REUSE_ASSESSMENT.md ไม่คัดลอกทั้งระบบ; local changes UNKNOWN |
| ADR-002 | ใช้ stdlib Python + SQLite + simple Thai browser UI สำหรับ first slice | รันและตรวจ transaction ได้โดยไม่มี dependency install; เปลี่ยน stack เมื่อ repo integration หรือ concurrency ต้องการ ไม่ถือเป็น production stack lock-in |
| ADR-003 | เลือก document completeness synthetic เป็น first slice | ทดสอบ full review/commit loop ได้โดยไม่ต้องมีโมเดลหรือข้อมูลผู้ป่วยจริง; 4 Champion เป็น candidates ไม่ใช่ product efficacy ที่ยืนยัน |
| ADR-004 | mock เป็น explicit profile; external routes fail closed | ไม่มีสิทธิ์ใช้ paid API/compute และ exact endpoint ยัง UNKNOWN; ไม่ fallback เงียบ |
| ADR-005 | แยก app deployment และ inference location | ป้องกัน frontend/server/local semantic ambiguity; route ต้องทดสอบจาก backend จริง |
| ADR-006 | ตรวจ permission และ input versions ที่ commit อีกครั้ง | ป้องกัน stale approval และ TOCTOU; SQLite transaction ครอบ result/audit/idempotency |
| ADR-007 | reviewer edits เปลี่ยนรุ่นและต้องตรวจใหม่ | ผูกสิ่งที่อนุมัติกับสิ่งที่ persist จริง; เก็บประวัติแก้เพื่อ evaluation |
| ADR-008 | registry ไม่เลือก exact Qwen/Typhoon/MedGemma แทนเจ้าของ | requested family ไม่ใช่ model identity; hardware, terms และ task evaluator ยังขาด |
| ADR-009 | specialist DR/CAD มีสัญญาและ evaluator ของตน | modality/quality/calibration ต่างจาก text; shared core ไม่แทนโมเดลเฉพาะด้วย LLM |
| ADR-010 | ไม่มี microservices, broker, orchestration framework ตอนเริ่ม | solo maintainability; เพิ่ม worker/outbox เมื่อมี durable external task ที่พิสูจน์ความจำเป็น |
| ADR-011 | clinical record signing/claim posting ยังไม่ implement | persisted result คือ synthetic document-completeness result ไม่ใช่ signed clinical note, diagnosis, claim หรือเงินรับ |
| ADR-012 | เก็บ unknown cost/usage เป็น null | ไม่ตีความไม่มีการวัดเป็นศูนย์; mock ไม่ใช่ราคาหรือ latency ของโมเดลจริง |

สมมติฐานที่แก้กลับได้: หนึ่งองค์กร synthetic, หนึ่ง patient journey, synchronous mock, fixture users/roles และภาษาไทยเป็นหลัก. ข้อมูลชนิดโรงพยาบาล, local SOP, retention, identity provider, hosting, concurrency, payer version, model endpoint และ budget ยังคง UNKNOWN. บล็อกเฉพาะงานที่ต้องใช้ข้อมูลนั้น; contracts/mock/docs เดินต่อได้

## v0.2 decisions

| ID | การตัดสินใจ | เหตุผล / ขอบเขต |
|---|---|---|
| ADR-013 | ใช้ candidate audit patch หลังตรวจ exact before hashes และ apply check | รัน baseline และ candidate checks ใหม่; ไม่แทน evidence ด้วยรายงาน audit |
| ADR-014 | React + TypeScript + Vite แยก apps/web; sidebar-01 เป็นฐาน | framework เดิมมีเพียง vanilla demo; retain legacy reference, pin actual packages และ template source |
| ADR-015 | Read-only fixture mode แยก API mode | หลาย fixture ช่วยตรวจ UI แต่ API ยังมีเพียง singleton; ไม่มี automatic write เมื่อเลือก fixture |
| ADR-016 | Strict boundary + integral-number normalization | reject bool/unknown/nested malformed ก่อน mutation; 1.0 มี semantics integer ก่อน hash |
| ADR-017 | Additive abstain_reason migration | เก็บเหตุผลเมื่อ reload; แถวเก่าคง null; rollback ใช้ pre-upgrade DB copy |
| ADR-018 | ไม่ bundle Synthea artifact เมื่อ artifact-specific rights ยังไม่ยืนยัน | เก็บ source/artifact metadata และ local authored fixtures; ไม่ถือ code license เป็น dataset license |
