# HIS POC starter v0.2.0 — เริ่มที่นี่

รอบนี้แก้ audit A01–A07 เพิ่ม frontend React/TypeScript/Vite และข้อมูลภาษาไทยสังเคราะห์ 18 กรณี. API runtime ยังคง **p-demo/e-demo/task-demo ชุดเดียว**; 38 domains เป็น navigation/ขอบเขตตามสถานะจริง. ไม่เปิด live inference หรือ deploy.

## 1. ตรวจ baseline

แนะนำ Python 3.12 พร้อม sqlite3 และ Node24/npm (ตรวจจริง Node24.22.1/npm11.9.0) ตาม apps/web/package-lock.json. รุ่นที่รันจริงดู VALIDATION_REPORT.

จาก package root:

```bash
python scripts/verify_hashes.py
python -m unittest discover -s tests -v
node --test tests/test_frontend_behavior.js
python -m pip install -r requirements-validation.txt
python contracts/check_contracts.py
python scripts/check_data.py
```

Core backend ไม่ต้อง pip install; jsonschema/Playwright ใช้สำหรับ validation เพิ่มเติมเท่านั้น. `generate_fixtures.py` สร้างข้อมูลเดิมซ้ำได้ ไม่ import DB.

## 2. เปิด backend และ frontend

Terminal A ที่ package root:

```bash
python -m src.his_poc.server
```

Backend อยู่ http://127.0.0.1:8080 ใช้ explicit mock และ SQLite. หน้า legacy reference ยังเปิดที่ URL นี้ได้. Terminal B:

```bash
cd apps/web
npm ci
npm run typecheck
npm test
npm run build
npm run dev
```

Frontend ใหม่อยู่ http://127.0.0.1:5173. เลือกโหมด fixture เพื่อดูข้อมูลและสถานการณ์แบบอ่านอย่างเดียว หรือเลือก API mode เพื่อทำ singleton journey จริง. ป้อน `demo-reviewer-token` สำหรับตรวจทาน หรือ `demo-viewer-token` สำหรับอ่านอย่างเดียว; เป็น public synthetic fixtures ไม่ใช่ provider credentials. UI ไม่อนุมาน permission จากชื่อ token; backend ปฏิเสธสิทธิที่ไม่อนุญาต.

API flow: โหลด context → แก้และบันทึกเอกสาร → สร้าง proposal → ดู evidence → บันทึก reviewer edits ถ้ามี → approve รุ่น/hash ที่ตรวจ → commit → reload result/audit. HTTP200 ของ proposal ไม่รับรอง success; ดู outcome. หลัง task completed จะสร้าง proposal ใหม่ไม่ได้ ให้ใช้ชื่อ DB ใหม่สำหรับ journey ใหม่ ไม่ลบหรือรีเซ็ตของเดิมเงียบ ๆ.

## 3. Environment และ persistence

`.env` ไม่ auto-load. `HIS_DB_PATH`, `HIS_PORT`, `HIS_DEMO_TOKEN` อ่านจาก backend shell. หากเปลี่ยน backend port ตั้ง HIS_PORT ใน shell ที่รัน Vite ด้วย; proxy target ถูกจำกัด loopback. บน PowerShell เช่น `$env:HIS_DB_PATH = "journey-02.sqlite3"`; บน Bash เช่น `HIS_DB_PATH=journey-02.sqlite3 python -m src.his_poc.server`.

อย่าชี้ v0.1 binaries ไป DB ที่ migrate แล้ว. อ่าน docs/MIGRATIONS.md และสำรอง DB เดิมก่อนเปิด v0.2 กับสำเนา. Default demo.sqlite3 เก็บข้อมูลเมื่อ restart; ไม่ใช่ production backup.

`npm run preview` ใช้ตรวจ production build เท่านั้น; fixture mode เปิดได้ แต่ API dev proxy อยู่ใน npm run dev. อย่าอ้าง production integration จาก preview ที่ยังไม่มี reverse proxy.

## 4. ส่งต่อ Codex

ส่ง ZIP นี้และวางข้อความใน STARTER_PROMPT_TH.md ให้ Codex. อ่าน CODEX_HANDOFF.md และ BACKLOG.md. งานแรก B00R ตรวจ baseline/browser จริง แล้ว B01R framework boundary โดยรักษา v1 contracts. ไม่ต้องรอ hardware/checkpoint/API key เพื่อทำงาน offline.

VALIDATION_REPORT แยก executed mock/isolated frontend checks/browser NOT_RUN. Synthea มีเพียง source inventory เพราะ artifact-specific redistribution ยัง UNKNOWN; ไม่มี external patient dataset อยู่ใน ZIP. ไม่ใช้ข้อมูล fixture นี้อ้าง clinical/product effectiveness.
