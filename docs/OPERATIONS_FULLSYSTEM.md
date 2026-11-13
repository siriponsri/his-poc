# Full-system local operations

รุ่นนี้ใช้ PostgreSQL 18.6 เป็นฐานหลัก ไม่มี SQLite fallback ในแอปใหม่ ข้อมูลเริ่มต้นและ inference เป็น synthetic / explicit mock เท่านั้น

## เปิดบน Windows ผ่าน Docker Desktop

เปิด Docker Desktop และเลือก Linux containers ก่อน จากโฟลเดอร์โครงการ:

```powershell
python scripts/dev.py init
python scripts/dev.py config
powershell -File scripts/run.ps1 up
```

`init` สร้าง `.env` ส่วนตัวด้วย secrets แบบสุ่ม ไม่เขียนทับไฟล์เดิม อ่าน `HIS_SEED_PASSWORD` ในไฟล์นี้บนเครื่องตนเองเพื่อ login บัญชี synthetic ที่ระบุใน seed เช่น `registration`, `clinician`, `operations_admin`, `auditor`, `patient` ห้ามแชร์ `.env` หรือใช้บัญชีทดสอบนี้กับข้อมูลจริง

คำสั่ง `up` เป็นการ initialize อย่างชัดเจน: DB readiness (timeout90s) → build → migration → seed → app → readiness (timeout90s) ถ้า migration fail จะไม่ seed หรือเริ่มแอป การเริ่มใหม่ใช้ `start` ซึ่ง migrate ได้แต่ไม่ seed:

```powershell
python scripts/dev.py start
python scripts/dev.py status
python scripts/dev.py logs
python scripts/dev.py stop
```

เปิด `http://127.0.0.1:8000/login` เป็น URL เดียวทั้ง frontend และ API มี deep-link fallback ฝั่ง FastAPI ค่า `HIS_WEB_PORT` เปลี่ยน host port ได้ Default publish เฉพาะ app บน loopback; DB ไม่มี published port `compose.debug.yaml` เป็น opt-in เมื่อจำเป็นต้องตรวจ DB ผ่าน localhost5432 เท่านั้น ไม่ใช้เป็น default

`docker compose up` ตรง ๆ ไม่ทำ migration/seed ให้ ต้องใช้ launcher หรือลำดับเดียวกันด้วยมือ ไม่ลบ volumes เพื่อแก้ migration failure และไม่มี reset command ใน launcher

## Native PostgreSQL

ต้องมี Python3.12+, Node24 ตาม lock และ PostgreSQL18 พร้อม `pg_dump`, `pg_restore`, `psql` ใน PATH ตั้ง `DATABASE_URL`, `HIS_SEED_PASSWORD`, `FILE_STORAGE_PROVIDER=local`, `FILE_STORAGE_ROOT`, `BACKUP_ROOT`, `WEB_DIST`, `HIS_ALLOWED_ORIGINS` ฝั่ง server เท่านั้น `.env.example` อธิบายค่าแต่ไม่ใช่ credentials ที่ใช้ได้:

```bash
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -r requirements-backend.txt
cd apps/web
npm ci
npm run build
cd ../..
python scripts/dev.py native-seed
python scripts/dev.py native-up
```

`native-seed` ตรวจ DB→migrate→seed; `native-up` ตรวจ DB→migrate→start โดยไม่ seed และ bind127.0.0.1 ห้ามใช้ trust authentication ของ test wrapper เป็น deployment config

## Health และ readiness

`/health` บอก process alive/build/profile เท่านั้น `/ready` ตรวจฐานข้อมูลและ migration ที่คาดหมายจริง ไม่สร้าง schema ไม่ seed และไม่รายงาน healthy หากยัง migrate ไม่ครบ D38 `/api/v2/operations/health` ต้อง login และมี D38.read แสดง PostgreSQL version, migration และความพร้อมของ pg tools แยกจากผล restore

Production HTTPS ต้องตั้ง Secure cookie และ allowed origins ให้ตรง การจัด reverse proxy/TLS/IdP ไม่ได้ deploy ในชุดนี้ ค่ารหัสผ่านฐานข้อมูลและ model keys อยู่ server; ไม่ใส่ `VITE_` prefix

## Backup / isolated restore

บัญชี `operations_admin` มี D38 operational privilege แยกจาก clinical authorization และต้องอยู่ใน server-only `HIS_PLATFORM_OPERATORS` ด้วย ค่า development ที่ประกาศใน Compose/.env คือ `user-operations_admin` เท่านั้น โดย native ที่ไม่ตั้งค่า allowlist จะปฏิเสธงาน global backup/restore การเพิ่ม role ผ่านหน้า admin ไม่สามารถเพิ่ม allowlist นี้ได้ `auditor` อ่าน job status ได้แต่สร้าง backup/restore ไม่ได้ นี่คือสิทธิสำรองทั้งฐานและ file store ของ deployment ไม่ใช่ export ข้อมูลผู้ป่วยของตนเอง ไม่เปิดดาวน์โหลด dump ผ่าน API ผู้มี D38.read ทั่วไปเห็นเฉพาะ job summaries ตาม organization/facility โดยไม่มี global file references/row fingerprints ส่วน full manifest จำกัดเฉพาะ platform operator

หน้า D38 เรียกงาน allowlist สองชนิด `backup` และ `isolated_restore`; ไม่มี arbitrary shell command งานมี requested/running/completed/failed หรือ restore_verified/restore_failed ใน PostgreSQL คำสั่ง CLI สำหรับ operator:

```bash
python scripts/backup.py --url http://127.0.0.1:8000
python scripts/restore.py BACKUP_ARTIFACT_ID --url http://127.0.0.1:8000
```

CLI ต้องมีแอปเปิดอยู่ และขอ operator username/password ผ่าน input/getpass หรือ `HIS_OPERATOR_USERNAME`/`HIS_OPERATOR_PASSWORD` ใน environment เท่านั้น ไม่รับรหัสผ่านผ่าน command arguments ไม่พิมพ์รหัสผ่าน และไม่เรียกฐานข้อมูล/pg tools โดยตรง CLI login ไปยัง backend บน loopback → สร้าง durable job ผ่าน route ที่ตรวจ platform allowlist/permissions → poll outcome → logout/revoke session ใน finally ทั้งกรณีผ่านและถูกปฏิเสธ URL ภายนอกและ URL ที่มี credentials ถูกปฏิเสธก่อนรับ password ถ้า timeout outcome ยังไม่ยืนยัน ให้ตรวจ job ID หรือรันซ้ำด้วย `--idempotency-key` ค่าเดิม ไม่สร้างข้อสรุปว่างานล้มเหลวหรือสำเร็จเอง

Backup ใช้ exported PostgreSQL snapshot ร่วมกันระหว่าง `pg_dump` กับ table inventory เก็บ counts และ canonical-row SHA256 ทุกตาราง พร้อมสำเนา file store/checksums; ตรวจแต่ละ DB reference ที่มี `file_path`/`file_sha256` ว่าไฟล์อยู่จริงและตรง hash หากไฟล์หายก่อน backup หรือเปลี่ยนระหว่าง copy งานต้อง fail และมี INCOMPLETE marker

Restore ตรวจ dump/file checksums ก่อน สร้างฐานใหม่ชื่อ `his_restore_<random>` และ file directory แยกโดยระบบเท่านั้น ไม่รับ active target จาก client ไม่ overwrite ฐานที่ใช้ บัญชี operator ต้องมี CREATEDB สำหรับงานนี้ ตรวจ row counts/hashes, validated FKs, file hashes และ DB-referenced files ตรง inventory ก่อนแสดง `restore_verified` หาก fail เก็บ isolated target สำหรับวิเคราะห์ ไม่มี auto drop DB

Backup รวม password hashes/session records จึงต้องป้องกัน artifacts เช่นข้อมูลอ่อนไหว ห้าม bundle backups/.env/live DB ใน release ค่าที่เผยใน job API เป็น metadata/checksums ไม่มี credentials/dump contents

## Worker interruption / recovery

Worker ตรวจสถานะบัญชี membership ปัจจุบัน และ platform allowlist อีกครั้งตรง tool boundary ก่อนเริ่ม dump/restore หากถูกถอนสิทธิ์ก่อน claim จะบันทึก failed/JOB_PERMISSION_REVOKED งานที่เริ่มโดยสิทธิ์ถูกต้องแล้วดำเนินต่อจนได้ outcome และ audit; logout ไม่ใช่ cancellation ของ job ที่ยอมรับแล้ว

FastAPI background worker ใช้ durable job table และเปิด transaction สั้นสำหรับ claim/finalize งาน ไม่ถือ actor lock ตลอด pg_dump งานที่ค้าง requested หลัง restart กด recover หรือ POST `/api/v2/operations/jobs/{id}/recover` เพื่อ schedule อีกครั้ง (worker claim row lock ป้องกัน double execution) running เกิน10นาที recover จะ mark failed พร้อม reason แล้ว operator ส่งคำขอใหม่ได้ ไม่สร้างผลสำเร็จปลอมและไม่ทับ artifact เดิม หาก worker เก่ากลับมาหลัง job ถูก mark failed จะไม่เปลี่ยนสถานะเป็นสำเร็จ

ตัวระบบยังไม่ใช่ HA worker queue การปิด process ระหว่างคำสั่งอาจเหลือ isolated target/artifact ที่ต้อง inspect/reconcile ตาม job error

## Automated disposable PostgreSQL tests

```bash
python scripts/test_with_postgres.py --pg-bin /path/to/postgresql18/bin -- .venv/bin/python -m unittest backend.tests.test_operations_pg -v
python -m unittest backend.tests.test_operations_unit -v
```

Wrapper สร้าง temporary cluster ที่มีเฉพาะ synthetic data, loopback-only และ trust auth เพื่องานทดสอบ ตั้ง DATABASE_URL/FILE_STORAGE_ROOT/BACKUP_ROOT ให้ child process และ shutdown เมื่อจบ เหมาะกับ CI ที่ loopback แยกตาม command; ไม่เปลี่ยนฐานเดิม `--keep` เก็บ cluster ไว้ inspect อย่างชัดเจน

## Runtime evidence boundary

`evidence/v0.3/operations` เก็บผลจริง Native PostgreSQL18.6 build/SELECT version รันแล้ว ส่วน Docker engine/Compose และ PowerShell execution ยัง NOT_RUN ใน environment นี้ ต้องรันบนเครื่องที่มี Docker/PowerShell ตามคำสั่งข้างต้น Image index digests และ PGDG client version ตรวจจาก registry/repository จริงและ pin แล้ว การ resolve digest ไม่ใช่ Docker startup verification
