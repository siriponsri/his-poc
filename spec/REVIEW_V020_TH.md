# รายงานตรวจ HIS POC Starter v0.2.0

วันที่ตรวจ: 2026-11-12  
ขอบเขต: ตรวจ source, contracts, data และพฤติกรรมซอฟต์แวร์แบบ read-only; ไม่แก้ starter และไม่เรียก live model  
ไฟล์ต้นทาง: `HIS_POC_Starter_v0.2.0_2026-11-12.zip`

SHA-256 ของ ZIP ที่ตรวจซ้ำจริง:

```text
2696a29275e9143f0f839968ed00d2ee97655487135e9dda3fa1ff5c748fb9ea
```

ทุก source path และเลขบรรทัดด้านล่างอ้างจากโฟลเดอร์ `HIS_POC_Starter` ภายใน ZIP นี้ ไม่ใช่โค้ดที่แก้แล้วในรอบรีวิว

## 1. ข้อสรุปและการตัดสินใจ

**เก็บ v0.2.0 เป็นฐานที่มีประโยชน์ แล้วส่ง Work ขยายเป็น Full Application Foundation ตามคำสั่งล่าสุด** ชุดนี้แก้ความถูกต้องของ core และเพิ่ม React frontend จริง แต่ยังไม่ใช่แอป HIS ครบระบบที่เข้า login แล้วทำงานต่อเนื่องตามบทบาทได้

ข้อจำกัดหลักเป็นเรื่องขอบเขต: มี document-review workspace, result/audit views และเมนู 38 domains ที่เข้า placeholder ยังไม่มี login/session/logout, role dashboard, patient registration/search, encounter/worklist หลายรายการ หรือธุรกรรมของแต่ละ domain การเพิ่มเมนูครบจึงไม่เพียงพอกับเป้าหมายใหม่ของผู้ใช้

พบข้อบกพร่องใหม่ใน **React state orchestration** ที่ existing tests ไม่ครอบคลุม โดยเฉพาะกรณี edit สำเร็จแต่โหลด context ต่อไม่สำเร็จ ทำให้ version/hash ที่แสดงกับ binding ที่จะส่งอนุมัติไม่ตรงกัน และกรณี commit error/read-back ที่ไม่คลาย pending state ควรแก้พร้อมเพิ่ม tests ก่อนนำ pattern นี้ไปใช้หลาย modules

รีวิวนี้ไม่พบหลักฐานว่า frontend ข้าม version/hash/permission guards ของ backend ได้ ผลที่ยืนยันคือ state และคำอธิบายในหน้าจอไม่สอดคล้องกัน ส่วนความพร้อมของ auth, database และ multi-patient เป็นงานฐานระบบที่ต้องเพิ่ม ไม่ควรเรียกว่าทำเสร็จจากการที่ bounded demo ผ่าน tests

## 2. สิ่งที่ตรวจและผลที่รันจริง

| รายการ | ผลรอบรีวิว / ความหมาย |
|---|---|
| Archive / integrity | 165 ไฟล์; 164 hashes ใน manifest ผ่าน และตรวจ ZIP SHA-256 ตรงค่าข้างต้น |
| Backend | 45 Python tests ผ่าน ครอบคลุม invariants ของขอบเขต synthetic demo |
| React adapter/state helpers | 17 tests ผ่านจาก `apps/web/tests/adapter.test.mjs` |
| Legacy HTML behavior | 12 tests ผ่านจาก `tests/test_frontend_behavior.js`; เป็นอีก frontend หนึ่ง ไม่ใช่ React app ใหม่ |
| Contracts | 23 schema definitions, 176 request/schema parity cases, 27 fresh local HTTP responses และ 27 frozen responses ผ่าน |
| Data | 18 authored Thai scenarios สร้างซ้ำและตรวจ hashes ได้; ไม่มี external patient dataset ถูก bundle และไม่มี backend import |
| New App state probes | รัน actual pre-render functions จาก `App.tsx` กับ hook/HTTP doubles พบข้อบกพร่องซ้ำได้ 3 กรณี ดู F20-01 ถึง F20-03 |
| Browser / visual / accessibility | **NOT_RUN ในรอบรีวิวนี้**; หลักฐานใน ZIP ก็ระบุ browser assertions executed = 0 |
| Typecheck / production build | ZIP มีหลักฐาน PASS ของผู้สร้างชุด; รอบรีวิวนี้ไม่ติดตั้ง dependencies และไม่รัน build/typecheck ซ้ำ |

คำสั่งที่ทีมรีวิวใช้สำหรับ suites หลัก:

```bash
# จาก starter root
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -q
node --test tests/test_frontend_behavior.js
python contracts/check_contracts.py

# จาก apps/web
node --test tests/*.test.mjs
```

จำนวน tests ที่ผ่านไม่ใช่จำนวน modules ที่ทำงานแล้ว และไม่ใช่ผลรับรองการใช้งานทางคลินิก การทดสอบ React เดิมตรวจ adapter กับ pure helper เป็นหลัก ไม่ได้เดิน actual component mutation → refresh → render จึงไม่พบ F20-01 ถึง F20-03

### ความหมายของ schema count

23 schemas แบ่งเป็น **16 implemented API shapes + 2 AI design + 4 specialist design + 1 integration-event design** คำว่า implemented shape หมายถึงรูปแบบ request/response/record ใน demo ไม่ใช่ 16 API endpoints หรือ 16 HIS modules ปัจจุบัน OpenAPI มี 6 operations รวม health/context และ 4 mutation routes

## 3. ขอบเขต frontend ที่มีอยู่จริง

| ความสามารถ | สถานะที่ตรวจพบ | หลักฐาน |
|---|---|---|
| React shell / sidebar | มีโครงจริงและ CSS รองรับจอหลายขนาด แต่ยังไม่มี browser QA ยืนยัน | `apps/web/src/App.tsx`; `apps/web/src/components/app-sidebar.tsx`; `apps/web/src/styles.css` |
| Navigation | Hash routes: workspace, results, audit, domains และ D01–D38 | `App.tsx:17`; `App.tsx:25`; `App.tsx:51`; `app-sidebar.tsx:5` |
| Login / logout / session | ไม่มีหน้า login, logout, session bootstrap หรือ current-user menu | `App.tsx:38`; `App.tsx:49`; `src/his_poc/server.py:28` |
| Authentication | พิมพ์ public demo bearer token เพื่อเชื่อม fixed context | `server.py:31`; `server.py:32`; `App.tsx:49` |
| Roles / permissions UI | ไม่มี actor/permissions read model; backend ตรวจสิทธิจาก demo users | `apps/web/README.md`; `src/his_poc/service.py:81` |
| Patient / encounter | API ใช้ p-demo/e-demo ชุดเดียว ไม่มี patient CRUD หรือ selector ของ runtime | `apps/web/src/lib/api.ts:26`; `api.ts:27` |
| Thai records | 18 records สำหรับอ่านและดู scenario; identifiers ไม่ใช่ backend patient IDs | `App.tsx:52`; `data/MAPPING.md:9`; `data/MAPPING.md:11` |
| Frozen snapshots | 27 HTTP responses; 6 context snapshots ให้เลือก แยกจาก 18 records | `apps/web/src/data/workflow.json`; `App.tsx:15`; `App.tsx:52` |
| Document workflow | มี save/propose/review/commit/result/audit สำหรับ singleton journey | `App.tsx:39`; `App.tsx:41`; `App.tsx:42`; `App.tsx:63`; `App.tsx:64` |
| 38 domains | 32 planned + 6 integration-planned; ไม่มี domain ที่สถานะ implemented | `docs/DOMAIN_SCOPE.csv`; `apps/web/src/data/domains.json` |
| Domain detail | ทุก domain เข้า template เดียวที่ระบุว่าไม่มี API/ธุรกรรมของ domain นั้น | `App.tsx:51` |
| Live inference | ไม่มี; UI และ runtime ระบุ explicit mock | `App.tsx:56`; `config/runtime.json` |

6 domains ที่ integration-planned คือ D10, D11, D20, D23, D24 และ D35 ส่วน D01, D03, D22, D34, D37 และ D38 มีคำอธิบายว่าได้เพียง partial shared-core demo ยังไม่ถือว่าทำเต็ม domain แล้ว

ข้อดีที่ควรรักษา: ไม่มี fixture-to-API fallback เงียบ ๆ, ไม่เรียก provider จาก browser, เก็บ metadata และ draft version, approval ผูก version/hash, failure/timeout/abstention แสดงแยกจาก success และมี template/license provenance อยู่ใน package

## 4. Findings ที่ควรแก้ก่อนขยาย frontend

### F20-01 — รุ่นที่แสดงกับรุ่นที่จะอนุมัติแยกจากกันเมื่อ edit สำเร็จแต่ refresh ล้มเหลว

**ลำดับ: P1 สำหรับความถูกต้องของ review UI** ไม่ใช่ข้อสรุปว่า backend authorization ถูกข้าม

ใน `App.tsx:41` หลัง POST review สำเร็จ ระบบเรียก `select(r.proposal)` แล้ว GET context ต่อ แต่ `select()` ที่บรรทัด 31 เปลี่ยนเฉพาะ binding/text/selection ขณะที่ตัวแปร proposal ที่แสดง derive จาก `ctx` ที่บรรทัด 22 หาก GET ล้มเหลว ctx ยังเป็นฉบับเก่า

ผลจาก reproduction ของฟังก์ชันจริง:

| สิ่งที่ตรวจ | ผลที่เกิด |
|---|---|
| Proposal version ที่ header ใช้ | 1 |
| Proposal hash ที่รายละเอียดใช้ | hash ของ v1 |
| Review binding | version 2 / hash ของ v2 |
| ข้อความใน review draft | ข้อความแก้ไขที่ server response รับแล้ว |
| reviewDirty | false |
| approvalReady | true |
| Binding ที่ request approve ถัดไปจะใช้ | version 2 / hash ของ v2 |

จุดแสดง header/hash คือ `App.tsx:57`; readiness และ binding helper คือ `apps/web/src/lib/api.ts:42` และ `api.ts:44` ปุ่ม “อนุมัติรุ่นที่แสดง” จึงมีหลักฐานหลายชุดบนหน้าจอที่ขัดกัน แม้ backend จะตรวจ request binding ตามที่ได้รับอยู่ก็ตาม

**แนวแก้:** เมื่อ mutation สำเร็จ ให้อัปเดต normalized proposal record จาก response ทันที หรือ disable subsequent review/approve จน reconcile ได้ ต้องมี invariant ว่า displayed proposal, review text และ action binding เป็น revision เดียวกัน เพิ่ม test ของ edit/approve/reject success ตามด้วย refresh failure

### F20-02 — Commit ที่ถูกปฏิเสธชัดเจนยังถูกเก็บเป็น unknown outcome

**ลำดับ: P2 ด้าน workflow recovery**

`App.tsx:42` ตั้ง pendingCommit ก่อนส่ง และ catch ทุก error ด้วยข้อความว่า “ยังไม่ยืนยันผลการบันทึก” โดยไม่แยก definitive rejection เช่น HTTP 409 STALE_CONTEXT ออกจาก response ที่หายจริง

Reproduction: POST commit ตอบ 409 STALE_CONTEXT → pending ยังคงอยู่ → GET context สำเร็จ → pending ยังอยู่ ปุ่มสร้างข้อเสนอใหม่/select/edit/approve ถูก disable ตาม pending แต่ error บอกให้โหลดข้อมูลแล้วสร้างข้อเสนอใหม่

ผู้ใช้ต้อง reconnect เพื่อทิ้ง state เดิม หรือ retry payload เก่าที่ stale ต่อไป ตัว browser script ใช้ workaround นี้โดยชัดเจนที่ `apps/web/scripts/browser_check.py:50` และ `:51` จึงยังไม่ใช่ recovery ตาม flow ปกติ

**แนวแก้:** แยกผลที่ทราบแน่ว่าถูกปฏิเสธจากผลที่ไม่ทราบเพราะ transport/5xx และกำหนด recovery ตาม code โดยรักษา key เดิมเฉพาะเมื่อยังจำเป็น ห้ามออก key ใหม่เพื่อเดาว่าการเขียนเก่าไม่เกิดขึ้น

### F20-03 — Read-back พบ result ที่ commit แล้ว แต่ pending state ไม่ถูกยืนยัน

**ลำดับ: P2 ด้าน reconciliation และข้อความบนหน้าจอ**

`App.tsx:32` และ `:36` โหลด context โดยไม่ reconcile pending operation กับ results กรณี response ของ commit หายแต่ read-back พบ proposal committed และ result ที่ผูกกันแล้ว ยังได้:

```text
readback_results = 1
displayed_status = committed
pending_still_unresolved = true
confirmed = null
```

ใน probe นี้ result เป็น committed read-back ที่จำลองจาก frozen HTTP fixture ไม่ใช่การเขียนฐานข้อมูลจริงของตัว reproducer ปัญหาที่พิสูจน์คือ actual App logic ไม่ปรับ pending/confirmed ตามหลักฐาน read-back

**แนวแก้:** ตรวจ matching operation/proposal/result ตาม identity ที่กำหนดใน contract แล้วแสดง confirmed result และคลาย pending เมื่อยืนยันได้ ไม่ใช้เพียง HTTP 200 ของ context เป็นหลักฐานว่า commit ใดสำเร็จ

### F20-04 — Skip link เปลี่ยน application route

**ลำดับ: P2; ยืนยันจาก source ยังไม่ใช่ browser assertion**

`App.tsx:46` ใช้ `href="#main-content"` สำหรับข้ามไปเนื้อหา แต่ hashchange ที่ `App.tsx:25` แปลงทุก hash เป็น route เมื่อใช้งานจาก results/audit ค่า route จะกลายเป็น main-content ซึ่งตกไป render workspace ตาม conditional ที่บรรทัด 54

**แนวแก้:** แยก focus navigation ออกจาก application router พร้อมกำหนด unknown route/not-found behavior ตรวจ keyboard path ใน browser จริง

### ข้อสังเกตการจัดโครง tests

17 tests ใน `apps/web/tests/adapter.test.mjs` มีคุณค่าและควรเก็บ แต่ควรเพิ่ม component/workflow tests สำหรับ state ที่เปลี่ยนพร้อมกันหลายชุด การทดสอบ helper อย่าง commitPayload หรือ bindReview อย่างเดียวไม่ตรวจว่าตัว App ใช้ response ถูกลำดับหรือแสดง record ที่ตรงกับ binding

## 5. ช่องว่าง backend, database และข้อมูลสำหรับ Full System

### Identity และ scope

`server.py:31` และ `:32` map bearer token ไปยัง users ที่ seed ไว้สองราย ไม่มี login/logout/session/me/user administration ขณะที่ตาราง users มี role เดียวและ patient assignment เดียว (`service.py:38`, `:85`) จึงยังไม่ใช่ role/scope model สำหรับเจ้าหน้าที่หลายแผนก

การเพิ่มหน้า login อย่างเดียวไม่แก้ส่วนนี้ ต้องมี backend-verified identity/session และ permission read model แล้วให้ UI แสดงเมนู/งานตามสิทธิ โดย backend ยังคงตรวจทุก action

### Singleton workflow

`service.py:12` กำหนด p-demo/e-demo/task-demo และ `document_completeness_task()` ที่บรรทัด 95 ตรวจ named task นี้โดยตรง ไม่มี persisted proposal→task binding ที่รองรับหลาย tasks การเพิ่มรายการผู้ป่วยใน frontend หรือ seed database หลายแถวจึงไม่ทำให้ระบบรองรับหลายผู้ป่วยอย่างถูกต้อง

หลัง task completed โค้ดไม่ reopen เงียบ ๆ ซึ่งถูกต้องสำหรับหลักฐานเดิม แต่การเริ่มงานใหม่ด้วย DB ใหม่ไม่ใช่ประสบการณ์ที่ยอมรับได้สำหรับ full application ต้องเพิ่ม task/encounter creation และ lifecycle ที่ใช้ฐานข้อมูลเดียวต่อเนื่อง

### Database integrity และ history

ทีมตรวจ backend สร้าง temporary DB และตรวจ schema: มี 12 tables, ไม่มี FOREIGN KEY declarations และไม่มี explicit NOT NULL constraints ใน DDL (`service.py:36` ถึง table audit ที่บรรทัด 47) การเปิด `PRAGMA foreign_keys=ON` ที่บรรทัด 72 ไม่ได้สร้างความสัมพันธ์ที่ยังไม่ประกาศ

service guards ยังทำงานตาม bounded tests แต่ full system ต้องมี database constraints, indexes และ scope relationships ที่ออกแบบจริง ไม่อาศัยทุก caller ทำถูกเสมอ

`update_document()` เขียนทับ current content และเพิ่ม version (`service.py:229`) จึงไม่มี historical document text ให้ reconstruct ต้นทางเก่าเพียงจาก hash/version Snapshot ของ proposal ไม่ทดแทน immutable document revisions เรื่องนี้มีบันทึกเป็นงานต่อใน backlog แล้ว ควรทำก่อนใช้เอกสารเป็น shared longitudinal record

transaction helper ใช้ SQLite `BEGIN IMMEDIATE` ทั้ง read และ write (`service.py:73`) การเปลี่ยน PostgreSQL จึงต้องทบทวน transaction/locking/migrations และ concurrency tests ไม่ใช่เปลี่ยน connection URL อย่างเดียว ดูแผนฐานข้อมูลใน `POSTGRESQL_DECISION_AND_MIGRATION_TH.md` ที่จัดทำแยกในชุดนี้

### ข้อมูลที่มีอยู่ไม่ได้เป็น multi-patient clinical dataset

18 Thai scenarios เป็น authored document/UI fixtures ไม่มีการแปลงเป็นอายุ diagnosis/allergy/lab values/financial amounts ตาม `data/MAPPING.md:20` ไม่มี backend import (`OPEN_DATA_MANIFEST.json:107`)

Synthea มี artifact inventory แต่สถานะ NOT_DOWNLOADED พร้อม null raw hash/retrieval/path (`OPEN_DATA_MANIFEST.json:117`, `:122`, `:126`) mapping FHIR เป็น specification ที่ NOT_IMPLEMENTED (`data/MAPPING.md:22`) จึงไม่ควรเขียนว่าได้คลังข้อมูลผู้ป่วยสาธารณะพร้อมใช้แล้ว

สำหรับ full scaffold ให้จัดทำ shared synthetic seed ที่มี provenance และ referential integrity ครบตาม journeys ก่อน ข้อมูลภายนอกที่ตรวจสิทธิ/format ได้แล้วค่อยนำเข้า staging ตามแผนข้อมูล ไม่แปลง fixture selection ให้ยิง mutation ไป p-demo

## 6. สิ่งที่ Work รอบใหม่ควรส่งมอบ

คำสั่งล่าสุดขยายจาก first-slice starter ไปสู่ **แอปครบโครงที่ทำงานสัมพันธ์กัน** จึงต้องแก้ GOAL/PLAN/BACKLOG/AGENTS ให้ตรงเป้าหมายใหม่ด้วย ไม่ส่งลำดับเดิมที่เริ่มและจบอยู่แค่การห่อ HTTP transport กลับไปอีกครั้ง

เกณฑ์หลักที่ควรใช้รับงาน:

1. **Login → role home → worklist** พร้อม current user/site/role, logout และ session recovery ที่ backend รองรับจริง
2. **Shared patient/encounter/task records** ค้นหา เพิ่ม เปิดงาน และอ่านหลัง reload ได้ในฐานข้อมูลเดียว; ข้อมูลเดียวกันแสดงข้าม modules
3. **38-module route/capability registry** แต่ละ module มี entities, scopes, list/detail/form/actions/history และสถานะ implementation ชัดเจน หน้า scope paragraph อย่างเดียวไม่ถือว่าผ่าน functional scaffold
4. **หลาย synthetic journeys ที่เชื่อมกัน** เช่น registration→queue→encounter; order→หน่วยรับงาน→result; pharmacy work→dispense record→charge; billing/claim draft; stock movement; admin/permission/audit
5. **Dashboard จาก records ที่มีสิทธิ** ไม่ใช้ metrics แต่ง และไม่ใช้ role switch บน client แทน authentication
6. **AI proposal/review เป็น shared capability** ที่เรียกจาก workflow ได้ตามสิทธิ มี evidence/version/provenance และไม่ทำให้ทุก module กลายเป็นหน้า document completeness เดียว
7. **แก้ F20-01 ถึง F20-04 และมีหลักฐาน browser จริง** สำหรับ login, navigation, permissions, entity context, mutation/reload และ recovery ที่เกี่ยวข้อง

ใช้ shared list/detail/form components ลดงานซ้ำได้ แต่ต้องมี field และ state transitions ที่มีความหมายกับแต่ละ domain การทำ generic task CRUD ไม่ได้แปลว่าทำ clinical signing, dispensing หรือ payer submission จริงสำเร็จแล้ว ส่วน integration ภายนอกที่ยังไม่มีให้ระบุความสามารถที่ทำได้ใน local synthetic workflow และสิ่งที่ยังรอ contract/endpoint แยกกัน

**เกณฑ์ที่ผู้ใช้ควรสังเกตได้:** เปิดแอปแล้วเข้า login เลือกงานตามบทบาท เปิดผู้ป่วย/encounter ทำงานใน module ที่เกี่ยวข้อง บันทึกแล้ว reload ยังอยู่ และติดตามข้อมูลข้ามหน่วยงานได้ โดยไม่ต้องเปลี่ยนชื่อ DB ใน terminal เพื่อเริ่มงานถัดไป

## 7. Reproduction artifacts และวิธีใช้

ไฟล์ในชุดรีวิวนี้:

- `reproduction/reproduce_frontend_state.mjs` — CLI อ่าน starter root ที่ส่งเข้าไป; ไม่แก้ source
- `evidence/frontend_state_reproduction.json` — structured observations พร้อม source SHA-256
- `evidence/frontend_state_reproduction.txt` — command, exit status, observations และ runtime warning

ตัวอย่างคำสั่งจากโฟลเดอร์ชุดรีวิว:

```bash
node reproduction/reproduce_frontend_state.mjs /path/to/HIS_POC_Starter
```

ต้องมี Node 24 ที่รองรับการ import erasable TypeScript ตามชุด starter ไม่มี npm install หรือ browser requirement Script ดึง pre-render functions จริงจาก App.tsx และใช้ HisApi/decoder จริง ร่วมกับ minimal useState/useEffect/fetch doubles เพื่อจำลอง mutation responses และ failed refresh

รอบนี้ได้ **3 cases executed / 3 defects reproduced**; exit 0 หมายถึง probe ทำงานครบ ไม่ใช่ application acceptance PASS มีการปรับ expiry ของ fixture ใน memory ให้เป็นเวลาปัจจุบัน +900 วินาทีเพื่อไม่ให้วันหมดอายุเก่ากลบปัญหา state ไฟล์ต้นทางไม่เปลี่ยน

ข้อจำกัด: ไม่ได้ render React DOM, ไม่ทดสอบ React scheduler หรือ interaction จริง, ไม่เรียก network/ฐานข้อมูลจริง และไม่ตรวจ layout/focus/accessibility จึงยังต้องเพิ่ม component tests และ browser acceptance สำหรับระบบที่ Work ขยายต่อ

## 8. ขอบเขตของข้อสรุป

รายงานนี้ให้ข้อสรุปด้าน software readiness และความสอดคล้องกับเป้าหมาย Full System ไม่รับรอง clinical effectiveness, production identity, external payer transactions หรือ live model quality ไม่มีการ deploy, training, paid inference หรือแก้ server dr-train ในรอบรีวิวนี้

ของเดิมที่มีหลักฐานควรเก็บและต่อยอด ส่วน scope gap ต้องถูกยกระดับเป็นงาน implementation ที่รับผลได้จริง และข้อบกพร่อง UI ที่ reproduce ได้ต้องไม่ถูกนับว่าปิดด้วยการผ่าน adapter tests เพียงอย่างเดียว
