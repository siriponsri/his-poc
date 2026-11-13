# HIS POC — เป้าหมายผลิตภัณฑ์ v0.2

วันที่จัดทำ 2026-11-12 · ผู้พัฒนา solo owner ร่วมกับ coding agents · สถานะ engineering starter

## ผลลัพธ์ที่ต้องการ

สร้าง HIS/ERP ที่ผู้ใช้ติดตามผู้ป่วย ครั้งรับบริการ งาน เอกสาร และผลธุรกรรมข้ามหน่วยงานได้ด้วย shared core เดียว และใช้ AI ช่วยเตรียมข้อเสนอที่ตรวจหลักฐานและทบทวนได้ วิสัยทัศน์ครอบคลุม 38 domains ใน `docs/DOMAIN_SCOPE.csv` แต่ starter ส่งมอบเพียงหนึ่ง synthetic journey ไม่มี domain ใดเสร็จครบสำหรับโรงพยาบาลจริง

กลุ่มผู้ใช้ตั้งต้นคือเจ้าหน้าที่จัดเตรียมเอกสาร ผู้ตรวจทบทวน และผู้ดูแลระบบ เจ้าของทางวิชาชีพ หน่วยบริการเป้าหมาย จำนวนผู้ใช้พร้อมกัน และ SOP จริงยังเป็น UNKNOWN จึงไม่ผูกระบบกับโรงพยาบาลขนาดใดล่วงหน้า

## ปัญหาและคุณค่าที่จะพิสูจน์

| ปัญหา | กลไกที่เสนอ | หลักฐานที่ต้องได้ |
|---|---|---|
| ข้อมูลและงานแยกตามแอป | patient/encounter และ task/document references ร่วม | ข้อมูลผิดผู้ป่วยถูกปฏิเสธทั้ง API และ tool boundary |
| ตรวจเอกสารซ้ำและไม่เห็นที่มา | evidence มีรหัส รุ่น ตำแหน่ง และข้อเสนอแยกจากผลที่รับรอง | replay จาก snapshot ได้; ผู้ตรวจเห็นสิ่งที่แก้ |
| AI เปลี่ยนข้อมูลโดยตรวจไม่ทัน | proposal → review → commit แบบผูก version/hash | stale approval และ retry ไม่เกิดรายการผิดหรือซ้ำ |
| เปลี่ยน provider แล้ว logic แตก | adapter contracts และ deterministic routing | contract suite เดิมผ่านเมื่อเปลี่ยน adapter ที่ยืนยันแล้ว |
| ประเมินแต่ครั้งที่สำเร็จ | run ledger รวม failure/timeout/abstention/edit/cost | รายงาน denominator ครบและไม่เติมค่าต้นทุนที่ไม่ทราบ |

## ขอบเขตที่ส่งมอบรอบนี้

เส้นทางแรก POC-01 คือ input → evidence → proposal → review → persisted result → audit ใช้ข้อมูลสังเคราะห์และ mock ที่ประกาศชัดเจน ผลสุดท้ายเป็นบันทึกการตรวจความครบถ้วนเอกสาร demo ไม่ใช่ clinical diagnosis, signed medical record, claim submission หรือรายการบัญชีจริง Shared core เป็นแบบขั้นต่ำของ patients, encounters, users/roles/scopes, documents, tasks, proposals, reviews, results, runs และ audit

POC-02 DR workflow, POC-03 claim completeness และ POC-04 CAD risk เป็น **candidates** ที่ยังไม่ถือว่า owner เลือกเปิดทุกงาน ไม่มีการฝึกโมเดลหรือใช้ paid API ใน starter ดูเหตุผล/ข้อมูล/evaluator ของแต่ละใบใน `pocs/`

## เป้าหมายที่วัดได้และเกณฑ์จบ starter

1. H01: แผนที่ 38 domains ตรง source IDs/ชื่อเดิม พร้อม owner/dependency/status/acceptance โดยไม่ยก partial demo เป็นทั้ง domain implemented
2. H02–H03: มี 4 candidate cards และหนึ่ง journey ที่ Codex รัน/ทดสอบต่อได้จากคำสั่งใน START_HERE โดยไม่ต้องเขียน spec ใหม่
3. R01–R03: mock journey บันทึก proposal, review, result และ audit จริงในฐานข้อมูล; UI ระบุ demo
4. R04–R06: meaningful regression tests ปฏิเสธ unauthorized/cross-patient/stale/duplicate-conflict และเก็บ failure โดยไม่แสดงเป็น success
5. H04–H05/R07: รายงานสิ่งที่อ่าน/ตรวจจริง, repo findings, UNKNOWN inventory, configuration ที่ไม่มี secrets และแยก declared/verified capabilities
6. ผลทดสอบจริงอยู่ใน VALIDATION_REPORT; การผ่าน engineering checks ไม่เป็นหลักฐาน effectiveness

## สมมติฐานที่แก้กลับได้

- เริ่มด้วย bounded document completeness task เพราะพิสูจน์ shared core ได้โดยไม่พึ่ง hardware/checkpoint หรือข้อมูลผู้ป่วยจริง
- ใช้ modular monolith และ relational persistence ก่อน; frontend เรียก backend เท่านั้น
- application deployment กับ inference location เป็นคนละ setting; cloud/dr-train/local ยังไม่พร้อมจนมี capability/integration evidence
- mock คือโหมดที่เลือกโดยเจตนา ไม่มี fallback เงียบจาก live ไป mock หรือ restricted data ไป cloud
- ใช้ namespace synthetic และ UTC timestamps ภายใน; แสดงวันที่ตามบริบทผู้ใช้ใน UI เมื่อเพิ่ม localization
- API deployment/framework migration สามารถเปลี่ยนหลังตรวจ repo เดิม โดยคง contract invariants และทดสอบซ้ำ

## ขอบเขตการตัดสินใจของ owner

Agent ทำเอกสาร coding และ synthetic tests ต่อได้เองภายใน scope ที่อนุมัติ ขอข้อมูลเมื่อถึงงานที่ต้องใช้จริง ได้แก่ repo ที่ต้องรวมงาน, hardware/endpoint, ขอบเขต compute/budget, สิทธิข้อมูล และ intended use/SOP ของ pilot UNKNOWN เหล่านี้บล็อกเฉพาะ integration หรือ evaluation ที่ขึ้นต่อข้อมูลนั้น ไม่บล็อก starter

ไม่ตั้งเป้าว่าจะสร้าง HIS ทั้งโรงพยาบาลได้ในเวลาที่ตายตัว ความสำเร็จทางธุรกิจ เช่นลดเวลาทบทวน ลด rejected claims หรือเพิ่มเงินรับจริง ต้องประเมินภายหลังด้วยข้อมูลและตัวเปรียบเทียบที่เหมาะสม แยกจากการเปิด endpoint ได้

## ขอบเขตเพิ่มใน v0.2.0

ปิด audit A01–A07 และเพิ่ม React/TypeScript frontend ใน apps/web จาก shadcn sidebar-01 ที่บันทึก provenance. UI มี 38 domain navigation โดยคงสถานะตาม inventory; placeholder ไม่แปลว่า implemented. ข้อมูลสังเคราะห์หลายกรณีอยู่ staging/fixture แบบอ่านอย่างเดียว; runtime API ยังคง p-demo/e-demo/task-demo ชุดเดียว. External data ที่สิทธิยัง UNKNOWN แจกเฉพาะ metadata.
