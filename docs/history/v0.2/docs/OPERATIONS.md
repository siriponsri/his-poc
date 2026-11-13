# Operations runbook

## Run local synthetic demo

กำหนดเป้าหมาย Python 3.11+; รันตรวจจริงบน Python 3.12.14 เท่านั้น (3.11 ยัง NOT_RUN). ใช้คำสั่งจาก root ของ starter. ไม่ต้องติดตั้ง third-party package สำหรับ runtime/test:

```bash
python -m unittest discover -s tests -v
python -m src.his_poc.server
```

ดู flags/env/port และ API ที่ implement จริงใน API_IMPLEMENTATION.md. เปิดเฉพาะ loopback และใช้ synthetic fixture เท่านั้น. หยุดด้วย Ctrl+C. `.env.example` เป็นเอกสาร ไม่ถูกโหลดอัตโนมัติ; ตั้ง shell environment ตาม platform ก่อนรัน. DB และ logs ระหว่างรันไม่ควร commit ใน git

## Readiness layers

| ชั้น | สิ่งที่ต้องยืนยัน | ปัจจุบัน |
|---|---|---|
| Local process | Python version, bind loopback, config parse | ตรวจใน VALIDATION_REPORT |
| Storage | schema initialize, transaction, persistence, integrity | demo tests เท่านั้น |
| Provider integration | endpoint identity/auth/TLS, protocol, schema, timeout/cancel | external NOT_RUN |
| Runtime capability | exact artifact+engine+parser, required capabilities | live UNKNOWN |
| Task effectiveness | evaluator dataset/threshold, human review burden | NOT_RUN |
| Clinical/production | intended use, SOP, clinical validation, security/operations | NOT_RUN |

การผ่าน health endpoint ไม่เท่ากับ model identity verification และไม่เท่ากับ effectiveness

## External preflight เมื่อมี inventory/authorization จริง

1. บันทึก config/runtime_inventory.json จากการอ่านเครื่องจริง: CPU/RAM/disk/GPU/VRAM/driver/engine/งานเดิม; ไม่ติดตั้งหรือ restart service เพื่อสำรวจ
2. ระบุ exact checkpoint/revision/hash/quantization, terms, prompt/template/parsers, token/image limits และ modality/preprocessing. ไม่รับรองสามโมเดลอยู่ GPU พร้อมกัน
3. ทดสอบ connectivity จาก backend location จริง; ใช้ allowlisted HTTPS/private route และ credentials references เท่านั้น ไม่ส่ง credential ใน URL หรือ log
4. ทดสอบ synthetic ขนาดเล็กหนึ่ง endpoint ก่อน; กำหนด deadline, max input/output, concurrency 1 เป็น starting experiment แล้ววัด memory/latency ก่อนเพิ่ม. เป้าหมายจริง UNKNOWN
5. Fill capability record ต่อ endpoint/model/config; ทดสอบ unsupported modality ต้อง reject ไม่มีการทิ้งภาพเงียบ
6. เปิด route เฉพาะข้อมูลและงบที่อนุญาต; default cloud_allowed_classes=[] และ approved_budget=null จึงยังปิดอยู่

## Failure/retry/cancellation

Mock scenario failure/timeout/abstention เป็นการจำลอง failure path ไม่ใช่ network timeout หรือการ cancel GPU งานจริง. บันทึก run outcome และ elapsed time ที่วัดได้; usage/cost ที่ไม่วัดเป็น null. ห้ามรายงาน success หาก schema invalid หรือไม่มี evidence ที่ใช้ได้

Local commit retry ใช้ idempotency key/payload เดิม; อย่าสร้าง key ใหม่เพียงเพราะ response หาย. ก่อน retry ตรวจ persisted result/audit และ reconcile state. External retry ต้องแยก transient เช่น timeout/429 กับ validation/policy errors; ไม่ retry authorization/schema errors. Design budget สูงสุดเริ่มที่ 0 automatic retries จน adapter กำหนด idempotency ของปลายทาง. Cancellation external ต้องบันทึก requested/acknowledged/unknown; ถ้า cancel acknowledgement ไม่มา อย่าอ้างว่างาน GPU หยุดแล้ว

## Backup / restore (local design procedure)

หยุด server ก่อนสำรอง. ใช้ SQLite backup API เพื่อสร้าง consistent copy แทนคัดลอกเฉพาะ .db ขณะ WAL ทำงาน. ตัวอย่างโดยแทน DB_PATH ตาม API_IMPLEMENTATION:

```python
import sqlite3
source = sqlite3.connect('DB_PATH')
target = sqlite3.connect('backup.sqlite3')
source.backup(target)
assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
source.close(); target.close()
```

Restore ลง path ใหม่ก่อน ห้ามทับต้นฉบับ; ตรวจ integrity, patient/encounter links, proposal/review/result/audit counts และ idempotency replay กับ synthetic copy แล้วจึงชี้ config ไปไฟล์ restored. Backup/restore drill สถานะ NOT_RUN เว้นแต่ VALIDATION_REPORT ระบุหลักฐานชัดเจน. Retention/RPO/RTO/backup encryption สำหรับ production ยัง UNKNOWN

## Rollout / rollback

Starter ไม่มี deployment. ก่อน rollout จริงให้ snapshot DB/config/contract/model revisions; รัน regression กับ synthetic fixture, disable outbound route จน tests ผ่าน. Rollback adapter/model configuration ห้ามลบ historical run/proposal/review. Schema rollback ต้องตรวจ backward compatibility และ restore plan; ไม่ย้อน migration ด้วยการลบทิ้งข้อมูล

## Audit / logs

จำกัดการอ่าน audit ด้วย permissions และ scope. เก็บ request/run/proposal/review/result identifiers, actor, versions, outcome, error class, latency, measured usage/cost. ไม่เก็บ secrets หรือ raw model reasoning. SQLite local audit ไม่ใช่ immutable external security log; access logs, retention, export, tamper evidence และ monitoring เป็น backlog. Rate/concurrency/load limits ของ production ต้องวัดแยกจาก local test

## v0.2 development frontend

ใช้ apps/web: npm ci → npm run typecheck → npm test → npm run build → npm run dev. Vite bind loopback5173 และ proxy เฉพาะ /api/v1 กับ /health ไป loopback8080 หรือ HIS_PORT. ไม่เปิด proxy สำหรับ arbitrary external endpoint. npm preview ใช้ตรวจ build/fixture ไม่มี API dev proxy. Production reverse proxy/auth/TLS ยัง NOT_IMPLEMENTED.

Frontend fixture mode เป็น read-only staging; API mode ใช้ singleton synthetic workflow. อย่า refresh frozen fixture เพื่อแก้คะแนนให้ผ่านโดยไม่บันทึก contract revision. ไม่เก็บ provider key ใน browser. Demo bearer token อยู่ใน memory เพื่อใช้ synthetic API เท่านั้น.

ก่อนเปิด v0.2 กับ DB เดิม อ่าน MIGRATIONS.md; additive abstain_reason มี tests แต่ไม่แทน production upgrade/restore drill. สำหรับ journey ใหม่หลัง task completed ใช้ DB path ใหม่และคงไฟล์เดิม. ไม่ล้างฐานข้อมูลอัตโนมัติเมื่อ npm/dev server เริ่ม.
