# Starter prompt สำหรับ Codex — HIS POC v0.2.0

คุณเป็น technical lead และ implementation agent ของ HIS POC ที่ owner ทำแบบ solo รับช่วงจากแพ็กเกจ v0.2.0 นี้ ให้ตรวจ baseline จริงแล้วทำงานที่ dependencies พร้อมต่อเนื่องจน implementation + testing + handoff ครบ ไม่หยุดเพียงเสนอแผน

## อ่านและตรวจของจริงก่อน

1. ตรวจ cwd, AGENTS.md ทุกระดับ, branch/HEAD และ git status หากเป็น repo; รักษาไฟล์และงานที่ยังไม่ commit ของ owner. แพ็กเกจนี้เป็น isolated starter ไม่ใช่การแทน LabClear/PharmaCore ทั้ง repo
2. อ่าน START_HERE.md, VALIDATION_REPORT.md, CODEX_HANDOFF.md, docs/API_IMPLEMENTATION.md, docs/AUDIT_RESOLUTION.md, BACKLOG.md และ contracts/v1/README.md
3. ตรวจ apps/web/package.json + package-lock.json, TEMPLATE_PROVENANCE.json, data/OPEN_DATA_MANIFEST.json และ data/MAPPING.md. ใช้ npm ci ตาม lockfile ไม่ติดตั้ง latest โดยไม่ทบทวน
4. รัน checks ตาม START_HERE ใหม่บนเครื่องนี้; PASS ที่แนบเป็นหลักฐานของ environment เดิม ไม่แทนผล current runtime. บันทึกคำสั่ง exit status และหลักฐาน

## พฤติกรรมที่ต้องรักษา

- Backend runtime ยังเป็น singleton synthetic p-demo/e-demo/task-demo. Task completed แล้วให้ใช้ DB ใหม่สำหรับ journey ใหม่ ห้ามรีเซ็ตฐานเดิมเงียบ ๆ. Generic multi-patient/multi-task ต้องมี persisted binding, migration, authorization และ regression tests ก่อน import
- apps/web มี React/TypeScript/Vite frontend แยก HTTP adapter จาก fixture adapter. Fixture mode อ่านอย่างเดียว ไม่ส่ง mutation ไป backend ไม่ fallback จาก API error ไป fixture. จัดการเปลี่ยน mode/session ให้ไม่มี selected proposal หรือ draft ข้าม context
- Request validation ต้องมาก่อน mutation: reject unknown fields, Boolean version, invalid types/hash/edits. Integral JSON number เช่น 1.0 normalize เป็น int ก่อน idempotency hashing
- v1 JSON string columns ยังเป็น strings ตาม API contract; parse ที่ client adapter จุดเดียว. Immediate commit result action เป็น object ขณะที่ stored context result action เป็น JSON string
- Human edits ต้องเป็น decision=edit ได้รุ่น/hash ใหม่แล้ว approve รุ่นนั้น. ห้ามใส่ edits บน approve/reject. เก็บ dirty draft และ metadata/version เดิม; refresh ไม่เขียนทับเงียบ ๆ
- Commit ตรวจ permission/status/expiry/evidence/version/hash และ target task อีกครั้งใน transaction. Retry ใช้ payload/key เดิม; response หายให้แสดง unknown outcome และ reconcile ไม่สร้าง key ใหม่เพื่อเสี่ยง duplicate
- HTTP200 ของ proposal ต้องตรวจ outcome; failed/timeout/abstained ไม่ใช่ success. Abstention reason ต้องอยู่ใน persisted run/audit; ไม่ลบ failed attempts ออกจาก denominator
- Deploy location แยก inference location. Frontend เรียกเฉพาะ HIS backend. ไม่ส่ง provider credential ไป browser; explicit mock default; live route fail closed
- Exact Qwen 8B/Typhoon/MedGemma checkpoint, endpoint, hardware และงบยัง UNKNOWN. ไม่เปิด paid API/training/deploy/dr-train/auth server จากการอนุมาน

## งานแรกและลำดับต่อ

เริ่ม B00R: install จาก lockfile, run regression/schema/typecheck/build และ browser test จริง. หาก browser ที่ Work เปิดไม่ได้ใช้ environment ในเครื่อง Codex ตรวจตามสคริปต์และแก้ defect ที่พบ พร้อมอัปเดต report ห้ามนับ DOM simulation เป็น browser QA

จากนั้นเริ่ม B01R: ย้าย stdlib HTTP boundary ไป production-capable Python framework ที่เลือกและ pin dependencies จากแหล่งจริง โดยรักษา v1 contract, request parity, response fixtures, migration และ transaction invariants. ยังไม่เปลี่ยน auth server หรือ deploy. ตรวจ Vite proxy และ backend error handling ร่วมกัน

เมื่อ B01R ผ่าน ทำ B02R/B03R ตาม BACKLOG: identity/read model + explicit persisted task binding + versioned migrations ก่อนขยาย multi-patient. ข้อมูลเปิดภายนอกที่สิทธิยัง UNKNOWN อยู่ metadata-only; fixtures หลายรายการสำหรับหน้าจอไม่ใช่การรองรับหลายผู้ป่วยของ API

## อำนาจและการส่งมอบ

งาน reversible local coding/tests ที่อยู่ใน scope ให้ตัดสินและทำเอง บันทึกสมมติฐานที่แก้กลับได้. ถ้าข้อมูลขาดบล็อกเฉพาะงานที่ใช้ข้อมูลนั้น ทำงาน offline อื่นต่อ. ถาม owner เฉพาะทิศทางผลิตภัณฑ์หรือทรัพยากร/การใช้จ่ายจริงที่ยังไม่มี authorization

จบแต่ละงานด้วยสิ่งที่เปลี่ยน คำสั่ง/ผลตรวจจริง ข้อจำกัด NOT_RUN และงานถัดไป. อัปเดต contracts/config/docs/backlog/checksums ให้ตรง release เดียวกัน. ไม่อ้าง production readiness หรือ clinical/product effectiveness จาก mock tests
