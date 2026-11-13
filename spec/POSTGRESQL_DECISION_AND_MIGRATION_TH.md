# เลือก PostgreSQL และแผนย้าย HIS POC สู่ฐานระบบเต็ม

วันที่ทบทวน: 12 พฤศจิกายน 2026 · เอกสารตัดสินใจและ brief ให้ Work ลงมือทำต่อ

## 1. ข้อเสนอที่ให้ใช้เป็นค่าเริ่มต้น

**เลือก PostgreSQL 18 เป็นฐานข้อมูลหลักของ application foundation รุ่นถัดไป** ใช้ backend แบบ modular monolith ด้วย FastAPI, SQLAlchemy และ Alembic รักษา frontend React + TypeScript + Vite ที่มีอยู่ ใช้ฐานข้อมูลหลักเดียวก่อน โดยแบ่งความรับผิดชอบของโมดูลในโค้ดและสัญญา API ให้ชัด

หน้า [PostgreSQL versioning](https://www.postgresql.org/support/versioning/) ที่ตรวจในรอบ 2026-11-12 ระบุสาย 18 ว่ายังได้รับการสนับสนุน และ minor ที่แสดงคือ 18.6 ให้ Work ตรวจ minor ที่รองรับอีกครั้งเมื่อเริ่มติดตั้ง แล้ว pin รุ่นและ image digest ที่ใช้จริงใน lock/config/evidence ไม่ใช้ tag `latest` ที่เปลี่ยนความหมายได้ การระบุรุ่นในเอกสารนี้ **ไม่ได้หมายความว่ามี PostgreSQL ติดตั้งหรือผ่านการทดสอบในชุด v0.2.0 แล้ว**

ให้ตรวจรุ่นที่เผยแพร่และรองรับจริงของ FastAPI, SQLAlchemy, PostgreSQL driver และ Alembic พร้อมความเข้ากันได้กับ Python ที่เลือก ก่อนเพิ่ม dependency ไม่บังคับ SQLAlchemy 2.0 เพียงเพราะตัวอย่างเก่าใช้รุ่นนั้น; เลือกรุ่น stable ที่ตรวจแล้วและ pin ทั้งชุด การจัด transaction ต้องอยู่ใน service/unit of work อย่างชัดเจนตาม [SQLAlchemy transaction documentation](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html) ส่วน [Alembic](https://alembic.sqlalchemy.org/en/latest/) ใช้จัดการ migration ที่มี revision และประวัติการเปลี่ยน schema

การเลือกนี้เป็นงานพัฒนาฐานแอปภายในขอบเขตที่ผู้ใช้ขอให้ขยายระบบ ไม่ต้องรอ endpoint ของ dr-train หรืออนุมัติ inference เพื่อทำฐานข้อมูล login และ synthetic workflows ต่อ

## 2. เหตุผลในการเลือก และสถานะของทางเลือก

| ทางเลือก | การตัดสินใจสำหรับโครงการนี้ |
|---|---|
| PostgreSQL 18 | ใช้เป็นฐานหลักสำหรับข้อมูลสัมพันธ์ ธุรกรรม และการทดสอบหลายผู้ใช้ร่วมกัน |
| MySQL/InnoDB | เป็นทางเลือกที่ใช้ได้; InnoDB รองรับธุรกรรมและการล็อกระดับแถว แต่ starter นี้ยังไม่มีระบบเดิมหรือความได้เปรียบเฉพาะที่ทำให้ต้องเลือก MySQL |
| SQLite | เก็บไว้รัน legacy demo และ unit tests ที่แยกขอบเขต ใช้เป็นข้อมูลต้นทางสำหรับ migration test ได้ แต่ไม่ใช้แทนฐานหลักหรือหลักฐานว่า concurrency บน PostgreSQL ผ่าน |
| Supabase | เป็น platform ที่ใช้ PostgreSQL ไม่ใช่ database engine คนละประเภท อาจเลือก hosting/auth ของ platform ภายหลัง; การเลือก PostgreSQL ครั้งนี้ไม่ได้บังคับใช้ cloud หรือ Supabase |
| pgvector | เป็น extension ทางเลือกเมื่อมีงานค้นคืนเวกเตอร์ที่กำหนด corpus และ evaluator แล้ว ไม่จำเป็นต่อ login, patient core หรือ transaction foundation |

อ้างอิงคุณสมบัติทางเลือก: [MySQL InnoDB](https://dev.mysql.com/doc/refman/8.0/en/innodb-introduction.html), [SQLite: appropriate uses](https://www.sqlite.org/whentouse.html), [Supabase database overview](https://supabase.com/docs/guides/database/overview), [pgvector](https://github.com/pgvector/pgvector) ข้อเสนอข้างต้นเป็นการตัดสินใจตามโครงงานปัจจุบัน ไม่ใช่ข้อสรุปว่า engine อื่นสร้าง HIS ไม่ได้

## 3. สิ่งที่ตรวจพบจริงใน v0.2.0

Backend ปัจจุบันใช้ stdlib HTTP กับ SQLite และ token สาธิตสองค่า ยังไม่มี login/logout/session หรือ `/me` ที่ใช้งานจริง `service.py` สร้าง 12 ตารางโดยไม่มี foreign key และไม่มี `NOT NULL` ที่ประกาศไว้ มีเพียง primary/unique indexes แม้เปิด `PRAGMA foreign_keys=ON` ก็ไม่มี foreign key ที่ประกาศให้ตรวจ

ผู้ใช้หนึ่งแถวมีเพียงหนึ่ง role และหนึ่ง patient assignment; workflow ผูก `p-demo/e-demo/task-demo` ไว้โดยตรง `documents` เก็บเนื้อหาปัจจุบันที่อัปเดตทับได้ ขณะที่ snapshot เก็บ ID/version/hash จึงย้อนสร้างข้อความต้นทางเก่าจาก hash เพียงอย่างเดียวไม่ได้ Migration ที่มีคือเพิ่ม `runs.abstain_reason` หนึ่งคอลัมน์ ไม่มี versioned migration framework ส่วน `db()` ใช้ `BEGIN IMMEDIATE` แม้ในงานอ่าน

ผลที่ตรวจซ้ำจริง: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -q` ผ่าน **45 tests** ใน SQLite/loopback scope นี้ การตรวจไม่ติดตั้งหรือเรียก PostgreSQL และไม่ใช่หลักฐานรองรับหลายผู้ป่วยใน backend ข้อจำกัดดังกล่าวถูกเปิดเผยใน `docs/API_IMPLEMENTATION.md`, `docs/MIGRATIONS.md` และ BACKLOG แล้ว

ให้รักษากติกาที่ทำได้ดี ได้แก่ permission checks, approval ที่ผูก version/hash, source staleness, reviewer revalidation, idempotency, atomic result/task/audit และ failure ledger แล้วเปลี่ยน persistence/transport ที่รองรับกติกาเหล่านี้ ห้ามเปลี่ยนเพียง connection URL แล้วนับว่าจบ migration

## 4. เจ้าของข้อมูลและขอบเขตตารางเป้าหมาย

ทุกโมดูลใช้ patient/encounter identifiers และ organization context ร่วมกัน แต่มี service เจ้าของการแก้ข้อมูล ไม่เขียนตารางของโมดูลอื่นจากหน้า UI โดยตรง

| โมดูลเจ้าของ | ข้อมูลหลักที่ต้องวางโครง | ขอบเขตของ foundation |
|---|---|---|
| Identity / access | users, identities, sessions, roles, permissions, scoped role assignments | Login ที่ทำงานจริง, logout/expiry/revocation, effective permissions; แยก system administration จากสิทธิอ่านข้อมูลผู้ป่วย |
| Organization | organizations, facilities, departments, reference data | บริบทสถานพยาบาล/แผนกและรหัสร่วม ไม่อนุมานสิทธิจากชื่อเมนู |
| Patient | patients, identifiers, contacts, patient access/care relationships | ลงทะเบียน ค้นหา เปิดรายละเอียดภายใต้สิทธิ; ออกแบบ merge/amendment แยก ไม่ลบประวัติเพื่อแก้ข้อมูล |
| Encounter | encounters, visits, statuses, assignments | เปิด/ปิด encounter และเชื่อม worklist โดยมี version และสถานะที่ตรวจได้ |
| Documents | documents, immutable document_versions, attachments | ข้อมูลใหม่ต้องเก็บ revision ที่อ้างอิงย้อนหลังได้; proposal ต้องชี้ revision จริง ส่วนต้นฉบับ legacy ที่หายแล้วต้องแสดง unavailable ตามข้อกำหนด migration ไม่ใช้ hash เป็นตัวแทนเนื้อหาที่หายไป |
| Workflow | tasks, assignments, proposals, proposal_versions, reviews, results | task ผูก patient/encounter/document อย่างถาวร; review/commit มีสถานะและการควบคุม concurrency |
| Clinical orders/results | orders, order_items, specimen/result references, result_versions | วาง ownership และสถานะ draft/reviewed/final/amended; เปิด workflow ที่ทดสอบแล้ว ไม่อ้างว่ารองรับ LIS หรือ clinical sign-off ทั้งหมด |
| Medication | prescriptions, items, dispensing references | แยกคำสั่งยาออกจากการจ่ายยา; เชื่อม patient/encounter และผู้มีสิทธิ โดยยังไม่อ้างว่ามี clinical decision support ครบ |
| Inventory | items, locations, lots, stock_movements | บันทึกการเคลื่อนไหวและเชื่อม transaction ต้นทาง; ไม่ให้ยอดคงเหลือเป็นตัวเลขที่แก้ตรงจากหลายโมดูล |
| Finance | charges, invoices, claims, payments, refunds, ledger entries | แยก billed/submitted/approved/gross_received/refunded/net_received/outstanding/cost โดย net_received = gross_received − refunded; outstanding อิง invoice adjustments/payment allocations ตาม policy; correction ใช้ธุรกรรมอ้างอิง ไม่เขียนทับ receipt/posting เดิมเป็นยอดสุทธิ |
| AI runtime | runs, evidence links, provider/config identity, usage/cost | AI เตรียม proposal ภายใต้สิทธิ; ไม่แก้ clinical/financial records อัตโนมัติ และไม่ทำค่า unknown ให้เป็นศูนย์ |
| Audit / integration | audit_events, security events, integration mappings | actor/scope/time/request/entity/outcome ค้นย้อนกลับได้; เพิ่ม outbox เมื่อเปิด external side effects จริง |

การมีตารางหรือ route สำหรับทั้งระบบยังไม่เท่ากับ implement กฎเฉพาะทางทุกโมดูล ใช้ข้อมูลสังเคราะห์ใน foundation และแยกรายงาน `implementation_status`, `verified_level`, `verification_status`, `external_integration_status` ตาม canonical matrix/acceptance โดย implementation_status บอกสิ่งที่สร้างแล้ว, verified_level ใช้ L0–L4 ตามหลักฐาน, verification_status ใช้ PASS/FAIL/NOT_RUN และ external_integration_status บอกสถานะ connector ไม่ใช้ NOT_RUN เป็น implementation status หรือยกผล SQLite tests เป็น PostgreSQL verified level

## 5. กติกา schema ที่ควรตัดสินใจตั้งแต่แรก

ใช้ relational columns สำหรับ identity, relationships, versions, state, ownership และจำนวนเงิน/ปริมาณที่ต้องตรวจสอบ ใช้ foreign keys, `NOT NULL`, unique และ check constraints กับความสัมพันธ์และกติกาที่ฐานข้อมูลตรวจได้ กำหนด organization/patient/encounter consistency ด้วยความสัมพันธ์ที่เหมาะสม เช่น composite keys/FKs ไม่พึ่งเพียงผู้เรียกส่ง ID มาถูกคู่ ดู [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)

ใช้ JSONB สำหรับ payload ที่มีโครงสร้างยืดหยุ่น เช่น normalized AI output, integration metadata หรือรายละเอียด audit ที่กำหนดสัญญาแล้ว ไม่ใช้ JSONB เป็นที่รวมทุกโมดูลจนไม่มีความสัมพันธ์หรือข้อจำกัด ตรวจ schema ของ payload ที่ boundary ด้วย [PostgreSQL JSON documentation](https://www.postgresql.org/docs/18/datatype-json.html) อธิบายความต่างของชนิด JSON/JSONB; ในโครงการนี้ต้องรักษา **canonical JSON bytes และ action hash ที่ใช้อนุมัติ** ไม่คำนวณใหม่จากรูปแบบข้อความที่ฐานข้อมูลส่งกลับโดยไม่มี compatibility test

- จำนวนเงินใช้ `NUMERIC`/Decimal พร้อม currency และกติกาปัดเศษที่ระบุชัด กำหนด precision ตามข้อมูลจริง; ห้ามใช้ floating-point เป็นยอดทางบัญชีที่ต้องตรงกัน
- เก็บเวลาที่เป็น instant ด้วย `timestamptz` และแปลงเขตเวลาใน UI; แยก date-only เช่นวันเกิดจาก timestamp ไม่เติมเวลา/เขตเวลาให้เอง
- ใช้ UUID สำหรับ ID ใหม่ได้ แต่เก็บ `legacy_id` หรือ migration mapping ของ `p-demo/e-demo` และ IDs เก่าอย่างชัดเจน ห้าม cast string เก่าเป็น UUID หรือทำ references หาย
- เอกสาร/ภาพขนาดใหญ่เก็บใน file/object storage ที่กำหนดสิทธิ เก็บ metadata, content hash, storage reference และ revision ในฐานข้อมูล ไม่ใส่ binary ทุกไฟล์ลง audit JSON
- สร้าง index จาก worklist/query ที่ใช้จริง เช่น organization, facility, patient, encounter, assignee, status และเวลา ทดสอบด้วย query plan หลังมีชุดข้อมูลสังเคราะห์ที่มีขนาดเหมาะสม

Row-level security ใช้เป็นการป้องกันเพิ่มเติมได้ แต่ไม่แทนการตรวจสิทธิใน backend หากเปิดใช้ ต้องทดสอบด้วย application role จริงที่ไม่ใช่ superuser และเข้าใจข้อยกเว้นของเจ้าของตาราง/บทบาทที่ bypass RLS ตาม [row security documentation](https://www.postgresql.org/docs/18/ddl-rowsecurity.html) การใช้ PostgreSQL หรือ RLS ไม่ทำให้ระบบได้รับรอง PDPA หรือมาตรฐานโรงพยาบาลโดยอัตโนมัติ

## 6. Transaction และ concurrency ที่ต้องคงไว้

PostgreSQL ใช้ MVCC และมีแนวทาง isolation/locking ของตน จึงต้องกำหนดจุดที่การตรวจสถานะกับการเขียนผลมีผลร่วมกันใหม่ ไม่ย้ายสมมติฐาน `BEGIN IMMEDIATE` มาตรง ๆ ดู [MVCC introduction](https://www.postgresql.org/docs/18/mvcc-intro.html) และ [explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html)

สำหรับ flow แรก แนะนำ transaction ที่ล็อก proposal และ target task ด้วยลำดับการล็อกคงที่ ตรวจ evidence revision และ current authorization ใน transaction เดียวกัน กำหนดนโยบายแข่งกันระหว่าง permission revocation, task cancellation และ commit ให้ทดสอบได้ หากเลือก SERIALIZABLE แทนบางส่วน ต้องมี retry สำหรับ serialization failure ตามขอบเขตที่กำหนด ทั้งสองแนวทางยังต้องมี unique constraints และการจัดการ conflict

ลำดับ first commit ต้องครอบคลุม:

1. ตรวจ actor และ scope จาก session ปัจจุบัน แล้วตรวจ idempotency key ที่ผูก actor/organization/operation และ payload เดิม
2. ล็อก/ตรวจ proposal, task และ evidence ที่จำเป็น ตรวจ version/hash, expiry, encounter status และสิทธิ reviewer ปัจจุบัน
3. เขียน result, ปรับ task version/status, บันทึก idempotency result และ audit ภายใน transaction เดียวกัน
4. หากเงื่อนไขใดไม่ผ่าน ให้ rollback ทั้งชุด; ถ้าเป็น replay ของรายการที่ commit แล้ว ให้คืน result เดิมหลังตรวจสิทธิ caller โดยไม่ทำ write ใหม่

**ห้ามถือ database transaction ค้างระหว่างรอ LLM หรือ network inference** อ่าน immutable input แล้วออกจาก transaction, เรียก provider, จากนั้นเปิด transaction ใหม่เพื่อตรวจสิทธิ/task/evidence ซ้ำและเก็บ outcome การ retry transaction ไม่ควรทำให้เรียกโมเดลซ้ำโดยไม่ตั้งใจ และต้องใช้ idempotency intent เดิมเมื่อ reconcile ผล commit

## 7. เส้นทาง migration และ API compatibility

**ขั้น A — เก็บ baseline:** ทำงานในรุ่น/branch แยก เก็บต้นฉบับ v0.2 และสำเนา SQLite พร้อม checksum รัน suite เดิมก่อนเปลี่ยน พร้อม inventory ตาราง จำนวนแถว และความสัมพันธ์ ไม่มีการเขียนทับไฟล์ฐานเดิม

**ขั้น B — สร้าง PostgreSQL foundation:** เพิ่ม Alembic revision แรก, connection/session management, migration command และ synthetic seed command แยกกัน ไม่ให้เริ่มเว็บแล้วสร้าง user/role หรือแก้ schema โดยไม่มี migration record ทดสอบ empty database → head และการเริ่มระบบซ้ำ

**ขั้น C — ย้ายข้อมูลสาธิตแบบมี mapping:** import จากสำเนา SQLite ตรวจ IDs, versions, hashes, nullable usage/cost, abstain_reason, review/result/audit references และ terminal task states ถ้าพบ orphan หรือค่าที่ไม่ผ่าน constraint ให้รายงานรายการและเหตุผล ไม่ลบทิ้งเงียบ ๆ

SQLite เดิมอาจไม่เหลือเนื้อหา document revision เก่าที่ proposal อ้างถึง เพราะเก็บเฉพาะ current content กรณีนี้ migration ต้องรักษา IDs/mapping, original hash, approvals/results และ audit ใน read-only legacy evidence unavailable หรือ quarantine พร้อมรายการ missing source อย่างชัดเจน ห้ามใส่ current text เป็นฉบับเก่า สร้างข้อความย้อนหลัง หรือเปลี่ยน hash ให้ผ่าน constraints ห้าม new commit บน proposal ที่ขาด required evidence revision การอ่านหรือ idempotent replay ของผลเดิมยังต้องตรวจสิทธิและไม่สร้าง write ใหม่ เกณฑ์ข้อมูลใหม่ต้องมี immutable history ครบ; legacy ที่ต้นฉบับหายแล้วต้องผ่านเกณฑ์การรักษาหลักฐานที่มีและรายงาน gap แทนการอ้างว่ากู้ข้อความเดิมได้

**ขั้น D — เพิ่ม auth และ multi-patient contracts:** ออกแบบ `/api/v2` สำหรับ login/session/me, patients, encounters, documents/revisions และ task-bound workflow เป็นชุดแรก ส่วน order/result/medication/inventory/finance เปิดตาม capability ที่ implement จริง ชื่อ endpoint ทั้งหมดในขั้นนี้เป็นข้อเสนอให้ Work เขียน contract ไม่ใช่ endpoint ที่มีอยู่แล้ว

**ขั้น E — ย้าย frontend ตาม module:** รักษา `/api/v1` และ DTO เดิมผ่าน compatibility adapter จน frontend ที่ใช้มันย้ายครบ แต่ใช้ session/permissions/scope middleware ชุดเดียวกับ API ใหม่ ไม่เก็บ public demo bearer-token handler เป็นทางเข้าอีกช่อง ประกาศ auth migration ให้ผู้เรียกทราบ; default application profile ต้องปฏิเสธ token สาธิตเดิม หากต้องรัน regression เดิมให้ใช้ isolated legacy profile ที่ปิดโดย default แยกฐานข้อมูลและ listener จากแอปใหม่ อย่าสลับ JSON-string columns เป็น expanded objects ใต้ contract เดิมโดยเงียบ ๆ ให้ React ใช้ `/api/v2/me` และ capability จาก server พร้อมล้าง patient context/draft เมื่อ session หรือ scope เปลี่ยน

**ขั้น F — ตรวจ restore และส่งต่อ:** สำรอง/กู้คืน PostgreSQL ในสภาพแวดล้อมทดสอบ แล้วเทียบ IDs, row counts, references, hashes และผลธุรกรรม เลือกวิธี backup/restore ตาม [PostgreSQL backup documentation](https://www.postgresql.org/docs/18/backup.html) การมี volume หรือไฟล์ dump อย่างเดียวไม่ใช่ผลทดสอบ restore; rollback ต้องบอกได้ว่าใช้ app/schema รุ่นใดและรักษาข้อมูลที่เขียนหลัง upgrade อย่างไร

## 8. การเปิดระบบในเครื่องและ PowerShell

ให้ Work จัด local Docker Compose สำหรับ PostgreSQL, backend และ frontend พร้อม health checks, persistent development volume และ configuration ตัวอย่างที่ไม่มี secrets จริง Default publish เฉพาะ web entrypoint บน `127.0.0.1`; PostgreSQL/backend อยู่ internal network และไม่ publish host ports หากต้อง debug ให้ใช้ explicit profile ที่ bind ports บน `127.0.0.1` เท่านั้น ค่า `DATABASE_URL` อยู่ฝั่ง backend ไม่ส่ง connection string หรือรหัสผ่านฐานข้อมูลเข้า Vite/frontend bundle ไม่ต้อง deploy cloud เพื่อผ่าน foundation

PowerShell launcher ที่ต้องส่งมอบควรตรวจ working directory, Docker engine และ Compose ก่อนเปิดระบบ ลำดับเริ่มครั้งแรกคือเริ่ม PostgreSQL → รอ database readiness ภายใน timeout → รัน explicit migration → รัน explicit seed เมื่อเลือกคำสั่งหรือ flag นั้น → เริ่ม application และรอ application readiness ห้ามรอ application readiness ก่อน migration เพราะ schema ยังไม่พร้อม หาก migration ล้มเหลวต้องหยุดไม่เปิดแอปเป็น ready และไม่ seed ต่อ Startup/restart ปกติไม่ seed หรือ reset ข้อมูลเอง หากไม่มี Docker แต่ผู้ใช้กำหนด `DATABASE_URL` ของ development PostgreSQL ที่มีอยู่ ให้รองรับ native fallback ที่ตั้งใจเลือกและใช้ลำดับตรวจฐาน/migration/seed/app เดียวกัน

หากทั้งสองวิธีไม่พร้อม ให้จบด้วยข้อความสาเหตุและขั้นตอนแก้ที่ชัด พร้อมระบุ PostgreSQL execution ว่า `NOT_RUN` ทำงาน code/schema/frontend ที่ไม่ขึ้นกับฐานจริงต่อได้ **ห้าม fallback เป็น SQLite เงียบ ๆ แล้วรายงานว่า PostgreSQL ผ่าน** Launcher ต้องไม่ลบ volume, reset schema หรือเปลี่ยน shared server เพียงเพื่อให้เดโมเริ่มได้

## 9. เกณฑ์รับงานก่อนเรียกว่า application foundation

| กลุ่มตรวจ | หลักฐานที่ต้องได้บน PostgreSQL จริง |
|---|---|
| Installation / migration | รุ่นและ image digest/driver ที่ใช้จริง, DB readiness → explicit migration → explicit seed → app readiness, fresh migration/restart/upgrade, seed แยกจาก startup และ default host exposure เฉพาะ web บน `127.0.0.1`; debug ports เปิดผ่าน profile ชัดเจน |
| Login / permissions | Login สำเร็จ/ล้มเหลว, logout, expiry, revoked user/session, effective permissions และข้าม role/organization/patient ถูกปฏิเสธทั้ง UI/direct API รวม v1 compatibility; default app ไม่รับ public demo tokens และ legacy profile/DB แยกชัด |
| หลายผู้ป่วย/งาน | หลาย patient/encounter/task ใช้งานได้จริง; proposal ผูก task และ revision ที่เลือก; ไม่มีการปิดงานข้ามกันหรือส่ง fixture patient ไปแก้ p-demo |
| Concurrent commit | same key คืนผลเดียว, different keys ไม่ลงซ้ำ, สอง proposals ของ task เดียวไม่จบซ้ำ, เปลี่ยน source/task/permission ระหว่างงานแล้วได้ผลตาม policy |
| Atomic failure | fault ก่อน/ระหว่าง commit ไม่เหลือ result/task/idempotency/audit บางส่วน และ retry/reconciliation คืนสถานะที่ตรวจสอบได้ |
| Evidence / history | revisions ที่สร้างใหม่หรือมีต้นฉบับย้ายมาครบอ่านกลับและตรวจ hash ได้, edits ต้องอนุมัติฉบับใหม่, immutable records ไม่ถูก update ทับ; legacy missing source ถูกระบุ read-only unavailable/quarantine ไม่แต่งข้อความเก่าและไม่เปิด new commit บนหลักฐานที่ขาด |
| Backup / restore | กู้คืนไปฐานทดสอบใหม่แล้วเทียบ identifiers, versions, hashes, references และผลที่ commit แล้ว ไม่ใช่เพียงตรวจว่า backup command ออก 0 |
| Frontend integration | Login → shared patient context → encounter/worklist → document → mock proposal → review → commit → reload/audit ผ่านจาก browser พร้อม session-switch และ permission-negative cases |

ให้รายงานแยก SQLite legacy tests, PostgreSQL integration tests, browser tests และสิ่งที่ `NOT_RUN` พร้อมคำสั่ง/exit status/หลักฐานจริง ก่อนเปิดโมดูลเพิ่มต้องระบุว่ากฎธุรกิจใดมี persistence และ acceptance แล้ว โครงทั้งระบบควรเชื่อม login, permissions, patient context และงานร่วมกันได้ โดยไม่ยกการผ่าน foundation ให้เป็นการรับรอง workflow ทางคลินิก/การเงินหรือ HIS ทั้งโรงพยาบาล

**งานของชุด brief นี้สิ้นสุดที่การตัดสินใจและข้อกำหนดส่งต่อ:** ยังไม่ได้ติดตั้ง PostgreSQL, เขียน Compose/launcher, เปลี่ยน schema หรือเรียกบริการจริง ขั้น implementation เป็นงานถัดไปของ Work/Codex ตามแผนข้างต้น
