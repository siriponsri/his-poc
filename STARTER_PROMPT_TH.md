# ทำงานต่อจาก HIS POC v0.3.0 ที่ผ่านการตรวจ local แล้ว

ทำงานใน checkout นี้โดยอ่าน AGENTS.md, START_HERE.md, GOAL.md, PLAN.md, BACKLOG.md, CODEX_HANDOFF.md และ VALIDATION_REPORT.md ก่อน ตรวจ Git และโค้ดจริงทุกครั้ง เก็บงานเดิมของผู้ใช้ไว้

หลักฐานรอบ 13 พฤศจิกายน 2026 ครอบคลุม 38 domains ที่ L2 และ J01–J10 ที่ L3 บน PostgreSQL และข้อมูลสังเคราะห์ ตรวจรายละเอียดจาก coverage และรายงานต้นทาง ไม่ใช้เพียงคำว่า PASS ในเอกสารแทนการตรวจ source และผลรัน

เปิดระบบด้วย python scripts/dev.py start เมื่อมีฐานและ seed แล้ว ห้าม reset หรือ seed ทับตอน restart รหัสผ่านอยู่ใน .env ส่วนตัวและห้าม commit

ก่อนแก้ให้ reproduce จุดที่เกี่ยวข้องในสภาพแวดล้อมทดสอบแยก ใช้ scripts/validate_fullsystem.py พร้อม --pg-bin และ --include-frontend โดยเลือก --output-dir ใหม่ ตรวจทุก exit code และอ่าน --help ของ browser scripts ก่อนใช้ การแก้ UI ต้องตรวจผ่านหน้าจอจริง ไม่ใช้ API-only แทนแล้วอ้างว่าผ่าน

รักษา shared identity/scope, immutable revisions, approval ที่ผูก version/hash/evidence, การตรวจสิทธิ์ซ้ำก่อนเขียน, atomic audit/ledger และ idempotency การบันทึก security event ที่รอ DB ต้องไม่ขวาง event loop ของแอป

AI ทุกเส้นทางที่ตรวจแล้วเป็น explicit DEMO mock เท่านั้น รุ่นโมเดล hardware และ endpoint ภายนอกยัง UNKNOWN ไม่เปิด live API, training, deploy หรือแก้ production/server โดยไม่มีทรัพยากรและ authorization ที่ยืนยันใน session

หลังเปลี่ยน API/model ให้ export contracts และ data dictionary ตรวจ consistency อัปเดต coverage ตามผลจริง แล้วสร้าง ZIP พร้อมตรวจ CRC และ SHA-256 เก็บผล FAIL เดิมไว้ แยก PASS/FAIL, MOCK, NOT_RUN และ external L4 เสมอ
