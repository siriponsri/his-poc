# เกณฑ์รับมอบ Full System Development Prototype

วันที่: 12 พฤศจิกายน 2026  
เอกสารนี้เป็น **target acceptance สำหรับรุ่นถัดไป** ไม่ใช่รายการ tests ที่มีหรือผ่านใน v0.2.0 ผลที่ตรวจรอบนี้อยู่ใน `REVIEW_V020_TH.md` และ `evidence/`

## 1. การรายงานผล

ทุก case บันทึก ID, app/schema/build version, database engine/version, environment, command หรือ browser steps, expected/observed outcome, exit/assertion result และ evidence path ระบุ `PASS`, `FAIL` หรือ `NOT_RUN`; skipped test ไม่นับเป็น PASS

Domain coverage ใช้ D01–D38 จาก canonical matrix แยก `implementation_status`, `verified_level`, `verification_status`, `external_integration_status` พร้อมหลักฐาน ห้ามตั้ง L2 จากการมี table หรือ route อย่างเดียว และห้ามนับ SQLite tests เป็น PostgreSQL acceptance

L2 หมายถึง domain workflow ขั้นต่ำบันทึกใน PostgreSQL และตรวจ behavior จริง ส่วน L3 ต้องมี journey ข้ามโมดูลพร้อม integration/browser evidence L4 เป็น external integration ที่ตรวจแยก ไม่ใช้ระดับเหล่านี้รับรอง clinical production readiness

## 2. Installation, startup และข้อมูลคงอยู่

| ID | สิ่งที่ทำ | ผลที่ต้องเห็น |
|---|---|---|
| RUN-01 | เริ่มจาก checkout/ZIP ใหม่และฐาน PostgreSQL ว่างด้วยคำสั่ง initialize ที่เลือก seed ชัดเจน | dependency versions ตรง locks; DB readiness → explicit migration ถึง head → explicit seed → application readiness แล้วเปิด URL พบ login; ไม่รอ app ready ก่อน migrate |
| RUN-02 | ลงทะเบียนผู้ป่วย/สร้างงานผ่านแอป แล้ว reload และ restart services | records เดิมอยู่ครบ; ไม่มีการ reset/seed ทับ; ไม่ต้องเปลี่ยนชื่อ DB เพื่อทำงานใหม่ |
| RUN-03 | เริ่ม launcher ขณะ Docker engine ไม่พร้อม | ข้อผิดพลาดและทางแก้ชัดเจน; native `DATABASE_URL` ใช้ได้เมื่อเลือก; ไม่มี silent SQLite fallback |
| RUN-04 | เปิด production build ผ่าน URL/deep link จริง | static routes และ API same-origin ทำงาน; refresh ไม่ 404; login/session ทำงานนอก Vite dev proxy |
| RUN-05 | รัน migration/seed ซ้ำ | migrations ไม่มี drift; seed ไม่ duplicate และไม่ทับข้อมูลที่แก้ผ่านแอป |
| RUN-06 | ตรวจ config/frontend bundle/logs | ไม่มี DB password/API key/session secret ใน client bundle หรือ log ที่ไม่ควรมี |
| RUN-07 | ทำให้ DB readiness ช้าหรือ migration ล้มเหลวระหว่าง initialize | timeout/error ชัดเจน; ไม่เริ่ม app เป็น ready ก่อน schema พร้อม ไม่ seed ต่อเมื่อ migration fail และไม่ reset ฐานเพื่อแก้ปัญหา |
| RUN-08 | ตรวจ Compose/launcher และ listeners ใน default profile แล้วเปิด debug profile แบบ explicit | default host publish เฉพาะ web บน `127.0.0.1`; DB/backend อยู่ internal network; debug ports เปิดเฉพาะ profile ที่เลือกและ bind `127.0.0.1` ไม่เปิด `0.0.0.0` โดยปริยาย |

## 3. Login, session, authorization และ patient context

| ID | สิ่งที่ทำ | ผลที่ต้องเห็น |
|---|---|---|
| AUTH-01 | เปิด root/deep link โดยไม่มี session | login/unauthenticated state; ไม่มี patient data ถูกส่งมาก่อนตรวจสิทธิ |
| AUTH-02 | login ผิดและถูก; เรียก current-user | backend ตรวจ credential; permissions/memberships มาจาก server; generic failure message และ rate-limit behavior ตามที่กำหนด |
| AUTH-03 | logout แล้วใช้ session เดิมเรียก API | ถูกปฏิเสธ; UI/cache/draft/context ของผู้ใช้เดิมถูกล้าง |
| AUTH-04 | session หมดอายุ/ถูก revoke หรือ user disabled | read/write ถูกปฏิเสธตาม policy; UI แสดง recovery ที่ไม่ทำให้ข้อมูลของคนก่อนรั่ว |
| AUTH-05 | ส่ง role/scope/patient ID ปลอมใน request และยิง API โดยตรง | server ตรวจ assignment/action permission; การซ่อนเมนูไม่เป็น authorization เพียงอย่างเดียว |
| AUTH-06 | ข้าม organization/facility/patient scope ทั้ง read/write/export | ถูกปฏิเสธโดยไม่มี record existence/data leakage เกิน policy ที่กำหนด |
| AUTH-07 | เปลี่ยนผู้ป่วย A→B ระหว่าง request ของ A ยังช้า | response/draft ของ A ไม่ถูกใช้เขียน B; header/action binding ตรง context |
| AUTH-08 | ผู้ดูแลระบบพยายาม approve clinical action โดยไม่มีสิทธินั้น | ถูกปฏิเสธ; system admin ไม่เป็น clinical signer โดยปริยาย |
| AUTH-09 | patient portal user สองรายอ่าน ID ของอีกคน | เห็นเฉพาะ records ที่ผูก subject และ publish policy ของตน |
| AUTH-10 | cookie/session/CSRF ตาม development และ HTTPS profiles | HttpOnly, Secure เมื่อ HTTPS, SameSite และ CSRF protection ของ mutation ตรง config;ไม่มี token ใน localStorage |
| AUTH-11 | เรียก v1 compatibility ด้วย session ที่ขาดสิทธิ และเรียก default app ด้วย demo-reviewer-token/demo-viewer-token เดิมโดยไม่มี session | v1 ใช้ session/permissions/scope เดียวกับ API ใหม่; ปฏิเสธ public demo tokens ตาม auth contract ไม่มี token bypass หากเลิก mount v1 ให้ 404 และมี migration note ชัดเจน |
| AUTH-12 | ตรวจ default profile แล้วเปิด isolated legacy profile สำหรับ regression โดย explicit | legacy token handler ปิดโดย default; profile ทดสอบใช้ฐานข้อมูลและ loopback listener แยก ไม่อ่าน/เขียนหรือรับ session ของ application ใหม่ |

## 4. ฐานข้อมูลและ transaction ที่ต้องทดสอบบน PostgreSQL จริง

| ID | สิ่งที่ทำ | ผลที่ต้องเห็น |
|---|---|---|
| DB-01 | insert/update orphan reference และค่าที่ขัด required/unique/check constraints | PostgreSQL ปฏิเสธตาม schema; controller/service คืน error ตาม contract |
| DB-02 | import สำเนา legacy SQLite เข้า schema ใหม่ | mapping/row counts/references/version/hash/task terminal state ตรวจได้; orphan/missing source รายงานและรักษา IDs/audit ไม่ลบทิ้งหรือแต่งข้อมูลให้ผ่าน constraints |
| DB-03 | อ่าน revision เก่าที่สร้างในระบบใหม่ หรือย้ายมาพร้อมต้นฉบับ หลังแก้ current document | content/version/hash ตรงหลักฐานเดิม; revisions ที่ใช้อ้างอิงไม่ถูก overwrite ส่วน legacy ที่ไม่มีต้นฉบับตรวจแยกใน DB-14 |
| DB-04 | canonical action เดิมผ่าน JSONB import/export | hash ที่อนุมัติยังตรวจซ้ำได้ตาม canonicalization version; wire shape ไม่เปลี่ยนเงียบ |
| DB-05 | concurrent same-key commit จากหลาย connections | result เดียวและ response replay ตรงกัน; audit/domain writes ไม่ซ้ำ |
| DB-06 | concurrent different keys ของ proposal/task เดียวกัน | ไม่ complete task/create result ซ้ำ; conflict มี outcome ชัด |
| DB-07 | เปลี่ยน evidence/task status/permissions แข่งกับ commit | outcome ตรง locking/serialization policy ที่ระบุ; ไม่มี partial writes |
| DB-08 | inject failure ก่อนและระหว่าง result/task/idempotency/audit writes | transaction rollback ตาม boundary; ไม่เหลือบางส่วนที่ทำให้ retry ตีความผิด |
| DB-09 | ขาย/จ่าย stock lot สุดท้ายพร้อมกัน และรับ/คืนรายการเดิมซ้ำ | ไม่มี negative stock ที่ policy ไม่อนุญาต; quantity conservation; retry ไม่เพิ่ม/ลดซ้ำ |
| DB-10 | จองเตียงหรือช่วงเวลาทรัพยากรเดียวพร้อมกัน | constraint/service concurrency policy ป้องกัน active allocation ทับกัน |
| DB-11 | ชำระ/คืนเงิน/แก้รายการบัญชี รวมรับ 800 คืน 100 และ retry รายการคืนเดิม | gross_received = 800, refunded = 100, net_received = 700; retry ไม่คืนซ้ำและไม่เขียนทับ gross receipt เดิม; outstanding ตรวจแยกจาก invoice adjustments/payment allocations ตาม policy; Decimal/rounding และ posting/reversal ถูกต้อง ไม่แก้ posted records ทับเพื่อให้ยอดตรง |
| DB-12 | ทำงาน mock inference ที่ล่าช้าและจำลอง provider error | ไม่ถือ DB transaction ค้างตลอด inference; ตรวจ evidence/permission ซ้ำเมื่อเขียนผล |
| DB-13 | หากใช้ RLS ให้ทดสอบ role/pool/connection context จริง | policies ใช้กับ runtime role ที่ตั้งใจ; ไม่มี stale tenant context หรือ owner/BYPASSRLS ทำให้เข้าใจผิด |
| DB-14 | import legacy proposal ที่อ้าง document revision ซึ่งต้นฉบับถูก overwrite ไปแล้ว | แสดง read-only legacy evidence unavailable/quarantine; รักษา IDs/mapping, original hash, approval/result/audit โดยไม่ใช้ current text แทนฉบับเก่า; new commit ที่ต้องใช้ต้นฉบับที่ขาดถูกปฏิเสธ การอ่าน/replay ผลเก่าที่ contract รองรับยังตรวจสิทธิและไม่สร้าง write ใหม่ |

## 5. React state และการ recover

| ID | สิ่งที่ทำ | ผลที่ต้องเห็น |
|---|---|---|
| UI-01 / F20-01 | edit proposal สำเร็จ v2 แล้ว GET context fail | displayed proposal/text/binding เป็น revision เดียวกัน หรือ action ถูกปิดจน reconcile |
| UI-02 / F20-02 | definitive commit rejection เช่น stale context | มีทางสร้าง proposal/review ใหม่ได้ตาม policy โดยไม่ reconnect/reset state ทั้งแอป |
| UI-03 / F20-03 | response commit หาย แล้วอ่าน matching result กลับ | pending ถูกยืนยันด้วย operation identity; แสดง result เดิม; ไม่ออก key ใหม่จนเกิด write ซ้ำ |
| UI-04 / F20-04 | ใช้ skip link จาก results/audit/domain route | focus ไปเนื้อหาโดยไม่เปลี่ยน route; keyboard flow ใช้งานได้ |
| UI-05 | switch session/patient/encounter และตอบ network ย้อนลำดับ | ไม่มี stale record/draft/action scope ปะปน |
| UI-06 | double click/retry/back/refresh ระหว่าง mutation | disabled/loading/outcome ตรง backend; คำว่า saved/approved ใช้เมื่อมีหลักฐานตอบกลับหรือ read-back |
| UI-07 | เปิด desktop และหน้าจอเล็กตาม viewport ที่ประกาศ | ตาราง/form/dialog อ่านและใช้ได้; ไม่มี control สำคัญตกนอกจอ; keyboard labels/focus/error states ตรวจจริง |

ใช้ component tests สำหรับ App orchestration และ browser tests สำหรับ rendered behavior หลักฐาน screenshot อย่างเดียวไม่พิสูจน์ persistence, authorization หรือ network recovery

## 6. Module coverage ทั้ง 38 domains

ให้ใช้ acceptance scenarios ราย domain ใน `DOMAIN_IMPLEMENTATION_MATRIX.md` เพิ่มอย่างน้อย:

- authorized happy path สร้าง/แก้/เปลี่ยนสถานะของ record จริงและอ่านกลับหลัง reload
- direct API permission-negative case ตาม scope ของ domain
- illegal transition หรือ duplicate/retry case ตามความเสี่ยงเฉพาะ
- shared-reference validation เช่น encounter/order/stock/financial document อยู่ใน scope เดียวกัน

กรณี domain ที่ไม่เหมาะกับ CRUD ทั่วไป เช่น audit, operations หรือ analytics ให้ตรวจ actions ที่มีความหมายตาม matrix โดยไม่เปิดแก้ audit หรืออนุญาต SQL อิสระผ่าน UI เพียงเพื่อให้มีฟอร์มครบ

Coverage report ต้องมีทั้ง 38 แถว โดยแยก `implemented_but_not_run` จาก `verified` รายการที่ยังเป็น placeholder ให้แสดงระดับจริง ไม่รวมเข้าผล Full System complete

## 7. Journey integration

ตรวจ J01–J10 ตาม `FULL_SYSTEM_SPEC_TH.md` ด้วย PostgreSQL และ browser จริง บันทึก actor/role และ record IDs ที่ส่งต่อข้าม module ให้ตรวจ tracing ได้

เน้นหลักฐานต่อไปนี้:

1. J01: ลงทะเบียนใหม่แล้ว clinician เปิด encounter และทำ document-review workflow ของคนเดียวกันได้
2. J02: lab order, specimen, result release/correction และ acknowledgment เชื่อมกัน
3. J03: medication order → authorized review → dispense lot → stock/charge เขียนอย่างสอดคล้อง
4. J04: admission/bed/transfer/nursing/discharge ไม่ทับ active allocation หรือผูกผิด encounter
5. J05: billed/submitted/approved/gross_received/refunded/net_received/outstanding/cost สะท้อน records ของแต่ละขั้น โดย net_received = gross_received − refunded; ยอดรับก่อนคืน ยอดคืน และยอดสุทธิตรวจย้อนถึง receipt/refund ได้ และ outstanding/cost ตรวจตามกติกากับข้อมูลต้นทางของตน
6. J06: request/approval/PO/receipt/issue/return/supplier references ถูกต้องและ retry ไม่สร้าง movements ซ้ำ
7. J07: role change/session revoke/direct API denial มีผลจริงและมี audit ที่เหมาะสม
8. J08: imaging file/report/DR task/referral มี patient linkage และ checksum; mock prediction ไม่ถูกติดป้ายเป็น live result
9. J09: maintenance/incident/corrective action/support requests และ report ใช้ shared asset/staff/facility records
10. J10: patient portal และ staff worklist เห็นคำขอเดียวกันตามสิทธิ ข้อมูลเผยแพร่ให้ subject ที่ถูกต้อง

การส่งข้อมูลไป payer/LIS/PACS หรือ live model ที่ไม่มี endpoint ให้รายงาน NOT_CONFIGURED/NOT_RUN แยกจาก local workflow ที่พิสูจน์แล้ว

## 8. Backup, restore และข้อมูลที่มาของ dataset

| ID | สิ่งที่ทำ | ผลที่ต้องเห็น |
|---|---|---|
| OPS-01 | backup PostgreSQL พร้อม records ที่สร้างจาก UI | ไฟล์/metadata/checksum และคำสั่ง restore ชัดเจน; no secrets in report |
| OPS-02 | restore ไปฐานและ file store ทดสอบใหม่ | อ่าน records/files/revisions/results ครบตาม backup inventory; IDs/references/hashes/counts ตรง; legacy missing-source flags คงเดิม ไม่อ้างว่ากู้ต้นฉบับที่ไม่เคยอยู่ใน backup ได้ และไม่ overwrite ฐานใช้งาน |
| OPS-03 | restore ทั้ง DB และ referenced documents/images | การสำรอง DB ไม่ถูกนับว่าครอบคลุม file storage อัตโนมัติ; missing files ตรวจและรายงานได้ |
| OPS-04 | inspect synthetic/open-data manifests และ import report | แยก authored/generated/downloaded/imported; license/source/version/checksum/mapping ตามจริง |
| OPS-05 | version/build/dependency/health/readiness checks | สถานะที่แสดงมาจาก runtime จริง; UNKNOWN/NOT_RUN ไม่แปลงเป็น healthy หรือ PASS |

## 9. Release gate

Full-system development acceptance ผ่านเมื่อ login/session/shared core ใช้งานได้, D01–D38 ถึง L2 ตาม matrix, J01–J10 ถึง L3, PostgreSQL concurrency/migration/restore และ browser journeys ผ่าน พร้อมส่ง source/runbook/coverage/evidence ที่ใช้ตรวจซ้ำได้

หากมี dependency ไม่พร้อม ให้ส่ง checkpoint ที่ใช้งานและพัฒนาต่อได้พร้อม gap list ไม่รายงานว่า full system ผ่าน สิ่งที่ยังแยกประเมินภายหลัง ได้แก่ live inference, external interface certification, clinical/product evaluation และ site-specific operations/SOP

## 10. เอกสารหลักที่ใช้ประกอบการออกแบบ tests

- [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [PostgreSQL row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [PostgreSQL backup](https://www.postgresql.org/docs/18/backup.html)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

การเลือก test cases และ acceptance levels เป็นข้อเสนอเฉพาะ HIS POC ของทีมรีวิว ไม่ใช่การกล่าวว่าเอกสารอ้างอิงรับรองระบบนี้
