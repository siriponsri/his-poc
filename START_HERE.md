# HIS POC v0.3 — ผ่าน local development acceptance

ผลรอบ 13 พฤศจิกายน 2026: 38 domains ที่ L2 และ J01–J10 ที่ L3 ผ่านบนข้อมูลสังเคราะห์ พร้อม Windows Docker, PostgreSQL, browser และ isolated restore ที่รันจริง อ่าน VALIDATION_REPORT.md และ coverage เพื่อดูขอบเขต หลักฐาน MOCK และ external L4 ที่ยังไม่ได้ตรวจ

## เปิดบน Windows ด้วย Docker Desktop

เปิด Docker Desktop และรอ Linux engine พร้อม จากโฟลเดอร์แพ็กเกจ:

```powershell
python scripts/dev.py init
python scripts/dev.py config
python scripts/dev.py up
```

`init` สร้าง `.env` ส่วนตัวพร้อมรหัสผ่านสุ่ม. `up` เป็นคำสั่ง initialize ที่เลือก migration+seed ชัดเจน; เริ่ม DB/รอ ready → migration → seed → application. เปิด http://127.0.0.1:8000/login ใช้ username จาก `backend/app/seed.py` เช่น registration, clinician, nurse, laboratory, imaging, pharmacist, billing, finance, inventory, quality, system_admin, auditor, patient. รหัสผ่านอ่านจาก HIS_SEED_PASSWORD ใน `.env` ของเครื่องคุณ ไม่ใช่ token สาธิตเดิม. ห้ามแชร์ `.env`

เปิดครั้งถัดไปใช้ `python scripts/dev.py start` ซึ่งไม่ seed. `stop` หยุดแต่เก็บ volume; `logs` ดูปัญหา. ไม่มีคำสั่ง reset/drop ใน startup. PowerShell wrapper: `./scripts/run.ps1 up`. หาก Docker engine ไม่พร้อม launcher จะแจ้งสาเหตุโดยไม่เปลี่ยนไปใช้ SQLite

## ทางเลือก native PostgreSQL18

ใช้ Python3.12+ และ Node24 ติดตั้ง dependencies ตาม locks:

```bash
python -m venv .venv
# Activate .venv for your shell first
python -m pip install -r requirements-backend.txt
cd apps/web
npm ci
npm run build
cd ../..
python scripts/dev.py init
```

ตั้ง DATABASE_URL เป็น development PostgreSQL18 ของคุณใน `.env` พร้อม FILE_STORAGE_ROOT/BACKUP_ROOT/HIS_ALLOWED_ORIGINS ตาม `.env.example`. ห้ามชี้ production DB. สร้าง database ว่างด้วยสิทธิของเครื่องคุณก่อน แล้ว:

```bash
python scripts/dev.py native-seed
python scripts/dev.py native-up
```

native-seed รอ DB → migrate → explicit seed. native-up รอ DB → migrate → start โดยไม่ seed. Frontend production build และ API อยู่ URLเดียว; refresh `/patients` หรือ `/domains/D10` จะคืน SPA แล้วตรวจ session. อ่าน `docs/OPERATIONS_FULLSYSTEM.md` สำหรับ backup/restore-to-isolated-target และข้อจำกัดการติดตั้ง

## ตรวจซ้ำ

```bash
python scripts/export_contracts_v2.py
python scripts/check_fullsystem_package.py
python -m unittest discover -s tests -v
node --test tests/test_frontend_behavior.js
cd apps/web
npm test
npm run typecheck
npm run build
```

Legacy tests ข้างต้นใช้ SQLite ที่แยกจาก default application. PostgreSQL suites และ browser commands ดู VALIDATION_REPORT; ต้องระบุ dedicated test DB ตามแต่ละ suite ห้ามชี้ข้อมูลสำคัญ. `scripts/test_with_postgres.py --pg-bin <PG18_BIN> -- <command>` สร้าง disposable PG cluster สำหรับ integration tests ที่เลือกอย่างชัดเจน

## ใช้งานต่อเนื่อง

เริ่ม role registration สร้าง patient/encounter. Clinical users มี care assignment ฝั่ง server; admin จัดสิทธิ์ให้ผู้รับผิดชอบก่อนเลือกผู้ป่วยใหม่. ใช้ document/task/proposal review ที่ผูก patient/encounter/version เดียวกัน. เปลี่ยนบทบาทด้วย logout/login หรือ membership ที่ server ยืนยัน. UI ไม่ให้ dropdown role กลายเป็นสิทธิเอง

ค่าเริ่มต้นของ AI คือ explicit mock และแสดง DEMO ชัดเจน ส่วนทางเลือก `dr_train_ollama` ใช้ Typhoon จริงเฉพาะการตรวจความครบถ้วนของเอกสารสังเคราะห์ ต้องเปิดใช้เองและตรึงรุ่นตามคู่มือด้านล่าง ผลจริงแสดง provider/model และไม่ติดป้ายว่าเป็น mock ไม่มีการสลับไปใช้ cloud หรือ mock อัตโนมัติเมื่อทางเลือกนี้มีปัญหา งานเชื่อมต่อภายนอกอื่นยังแยกตาม coverage ไม่มีการอนุมานว่าเชื่อมสำเร็จจาก workflow จำลอง

## ใช้ Typhoon จริงกับเอกสารสังเคราะห์แบบเลือกเปิด

อ่าน [docs/DR_TRAIN_AI.md](docs/DR_TRAIN_AI.md) ก่อนตั้งค่า ค่าเริ่มต้นยังเป็น `HIS_AI_PROVIDER=mock_demo` ผลผ่าน 38 domains และ 10 journeys เดิมเป็นหลักฐาน local workflow ที่ใช้ mock ไม่ใช่ผลทดสอบโมเดลจริงทุกเส้นทาง

ทางเลือกที่ตรวจแล้วใช้ `hf.co/scb10x/typhoon2.1-gemma3-12b-gguf:Q4_K_M` ผ่าน Ollama 0.12.6 บน dr-train ตรวจเอกสารไทยที่แต่งขึ้นสามกรณี ผ่าน browser workflow จริง 7 ข้อ และตรวจอ่านผลเดิมอีก 2 ข้อ ตัวอย่างหนึ่งใช้เวลา 11.205 วินาที รับเข้า 408 และส่งออก 141 tokens ตาม runtime ส่วนต้นทุนยังเป็น `null` ไม่ได้วัดเป็นเงิน MedGemma 27B พบว่าติดตั้งอยู่ แต่ยังไม่ได้ทดสอบ inference จึงไม่ต้องดาวน์โหลดโมเดลเพิ่มเพื่อทำงานขอบเขตนี้

ตั้งค่าทางเลือกนี้ใน `.env` ส่วนตัวตาม [.env.example](.env.example) และใช้ model/digest/engine pins จากคู่มือ กำหนด SSH target เป็น alias ที่คุณตั้งไว้เองใน SSH config ไม่ใส่ IP รหัสผ่าน หรือ private key ลงเอกสารหรือ repository สำหรับ app ที่รัน native ใช้ `http://127.0.0.1:18134` ส่วน Docker Desktop ใช้ `http://host.docker.internal:18134`

หลังตั้งค่าและเปิดใช้ `HIS_LIVE_SYNTHETIC_ENABLED=true` กับ `DR_TRAIN_TUNNEL_ENABLED=true` แล้ว:

```powershell
python -m pip install -r requirements-backend.txt
python scripts/dr_train_tunnel.py start
python scripts/dr_train_tunnel.py status
python scripts/dev.py start
```

ตัวช่วย tunnel ตรวจเฉพาะ metadata รุ่นของ Ollama และ model digest ไม่โหลดโมเดลหรือสั่ง inference คำสั่ง `dev.py start` และ `native-up` จะตรวจหรือเริ่ม tunnel ให้เมื่อเลือก profile นี้ไว้ชัดเจน โดยไม่ seed ข้อมูลใหม่ ถ้าตรวจเส้นทางหรือรุ่นไม่ผ่านจะไม่เริ่ม app ต่อ ค่าใน process environment มีลำดับก่อน `.env` จึงควรตรวจค่าที่ตั้งค้างไว้เมื่อต้องแก้การเชื่อมต่อ

เข้า D22 เพื่อบันทึกเอกสารสังเคราะห์ แล้วใช้ D37 กับงาน `document_review` ของผู้ป่วยและ encounter เดียวกัน ผลตรวจมีห้าหัวข้อพร้อมสถานะพบหลักฐาน ไม่พบหลักฐาน หรือยังไม่ชัดเจน และข้อความอ้างอิงจากต้นฉบับ ผู้ใช้ต้องอ่าน แก้ข้อความสรุปตามต้องการ อนุมัติรุ่นที่แสดง แล้วจึงยืนยันบันทึกผล ระบบไม่ใช้ผลนี้วินิจฉัยหรือสั่งการรักษา

เอกสารมีเพดานจำนวนอักขระ และยังต้องผ่าน guard ที่คิดจาก UTF-8 bytes กับพื้นที่ context จึงอาจถูกปฏิเสธก่อนถึงเพดานอักขระ โดยเฉพาะภาษาไทย อ่านรายละเอียดขนาดเอกสาร เวลารอ และการ retry ด้วยคำสั่งเดิมในคู่มือ

ไฟล์เริ่มส่งต่อ: `STARTER_PROMPT_TH.md` + `CODEX_HANDOFF.md`. เมื่อนำไปทำงานต่อ ให้ reproduce PG+browser บนเครื่องผู้รับก่อนแก้โค้ด ใช้ coverage และผลรันใหม่กำหนดงานต่อ ไม่ลดขอบเขตกลับไปเป็น placeholder

## Browser ที่ตรวจแล้วและการเก็บหลักฐานรอบใหม่

ติดตั้ง requirements-validation.txt และ Chromium ด้วย python -m playwright install chromium แล้วอ่าน --help ของ browser_check.py, browser_journeys.py, browser_domains.py และ browser_recovery.py ใต้ apps/web/scripts ทุกคำสั่ง --help ออกโดยไม่ login หรือแก้ข้อมูล

ตัวอย่างโหลดรหัสผ่านจาก .env เข้าสู่ process โดยไม่พิมพ์ค่าออกมา:

    python -c "import subprocess,sys;from scripts.dev import load_env;subprocess.run([sys.executable,'apps/web/scripts/browser_check.py','--base-url','http://127.0.0.1:8000','--output-dir','apps/web/evidence/fullsystem/new-smoke'],env=load_env(),check=True)"

เปลี่ยนชื่อ script เป็น browser_journeys.py, browser_domains.py หรือ browser_recovery.py และใช้ output directory ใหม่ของแต่ละรอบ Recovery ตรวจ restart และสร้าง backup/restore ลงฐานทดสอบแยกจริง ใช้กับข้อมูลสังเคราะห์ที่แยกไว้เท่านั้น

เก็บผลเดิมไว้เสมอ ใช้ --output-dir ใหม่กับ scripts/validate_fullsystem.py เช่นกัน สร้าง ZIP หลังงานนิ่งด้วย python scripts/package_release.py --output ../his-poc-v0.3.0-local.zip แล้วตรวจด้วย scripts/verify_hashes.py
