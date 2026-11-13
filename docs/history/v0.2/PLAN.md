# แผนตามผลลัพธ์ v0.2

Milestone ใช้หลักฐานเป็นเงื่อนไขจบ ไม่ใช่กำหนดเวลาและไม่บังคับเปิดทุก POC พร้อมกัน สถานะ execution ล่าสุดดู VALIDATION_REPORT; ตารางนี้กำหนดงานและเกณฑ์รับ

| Milestone | ผลส่งมอบและ acceptance | Dependencies | สิ่งที่ทำต่อได้ / stop เฉพาะงาน |
|---|---|---|---|
| M0 Starter baseline | H01–H05, R01–R07 เท่าที่ implement; contracts/config/docs สอดคล้อง; mock persisted journey | ไฟล์แนบและ runtime sandbox | ดำเนินงานได้; NOT_RUN ต้องมีเหตุผล/คำสั่งต่อ |
| M1 Core hardening | auth production integration, migrations, tests concurrency/restore, evidence revisions และ reviewer UX | M0; repo decision ก่อนรวมโค้ด | ทำ tests และ design ได้; real data use รอ policy/SOP |
| M2 One verified inference route | adapter native protocol, identity record, capability suite, policy/usage errors, network smoke จาก backend | M1 invariants; exact checkpoint/endpoint/resource authorization | ทำ mock adapter contract suite ต่อได้; หยุดแค่ live call ที่ยังไม่มีสิทธิ/งบ |
| M3 POC-01 offline comparison | frozen fixtures/prompts/tools, ครบทุก arm ที่จำเป็น, paired outcomes/failures/cost, go/hold | M2 สำหรับ model arms; evaluation/PROTOCOL.md | baseline/synthetic regressions ทำก่อน; ไม่มี clinical claim |
| M4 Candidate integration | เลือก POC-02 หรือ POC-03 ก่อน; bounded specialist/payer contract และ evaluator แยก | candidate-specific data/terms/SOP/contract | adapters/fixtures ทำได้; ห้ามสมมติ external service พร้อม |
| M5 Controlled pilot | intended use, owner, training/downtime/rollback, prospective measurements และ criteria ที่ตรึง | M3/M4 evidence + real-data authorization | หยุด pilot เมื่อ patient mix-up/unauthorized write/critical error; เก็บข้อมูลเพื่อแก้ |
| M6 Expand domain waves | domain acceptance ใน CSV ผ่านเป็นราย capability; migration/reconciliation และ responsible owner | M5 หรือ independent ready module | ไม่เปิด domain จากการผ่าน shared core เพียงอย่างเดียว |

## ลำดับขยายทั้งโรงพยาบาล

Wave A: D01 D03 D22 D34 D37 D38 เป็น shared foundation; D35 เป็นขอบเขตเชื่อมต่อ ทุกตัวมีงานจริงนอกเหนือจาก demo อีกมาก เช่น patient merge/unmerge, signed amendment, SSO, retention, restores และ terminology governance

Wave B: D10 D11 D20 D23 D24 ตาม candidate ที่เลือก เชื่อม LIS/image/referral/claim โดยรักษาเจ้าของข้อมูลและ external acknowledgement; งานทางคลินิกและการเงินมี evaluator คนละชุด

Wave C: D02 D04–D09 D12–D19 D21 เป็น clinical/access workflows ที่ต้อง SOP และเจ้าของงานเฉพาะ ไม่ใช้ template review หนึ่งชุดแทนการรับรองทุก workflow

Wave D: D25–D33 D36 เป็น ERP/quality/analytics/secondary use; เริ่ม reconciliation และ permissions ก่อน metrics dashboard ต้นทุนและเงินรับต้องมี ledger definitions

## งานที่เดินคู่ขนานได้

- contracts + synthetic fixtures + schema tests ทำได้ขณะรอ endpoint
- inspect existing repo ทำได้ก่อนตัดสิน merge; รักษา local modifications และสร้าง isolated branch เมื่อเหมาะสม
- DR/CAD contract design ทำคู่ขนาน แต่ไม่แก้ business logic ให้ผูก specialist model
- product/research protocol ทำคู่ขนานกับ UI และ auth; กำหนด evaluator ก่อนเห็น test results

ผู้รวมผลคือ technical lead ของรอบงาน ตรวจ GOAL/PLAN/ARCHITECTURE/contracts/config/BACKLOG ทุกครั้งที่เปลี่ยน scope และบันทึก ADR แก้ข้อขัดแย้งก่อนปิด milestone

## Acceptance และเหตุหยุดที่สัมพันธ์กับงาน

M0–M1 ต้องไม่ commit ข้าม patient/encounter, ใช้ approval ฉบับเก่า หรือสร้าง duplicate result; ถ้าพบแก้และรัน regression ก่อนส่งต่อ แต่ไม่หยุดการเขียนเอกสารอื่น
M2 ห้ามเปิด cloud fallback จน data policy และงบยืนยัน; invalid schema/timeout เป็น failure ที่เก็บได้ ไม่เปลี่ยนเป็น mock success
M3 รายงาน inconclusive/negative ตามหลักฐาน ไม่เพิ่มตัวอย่างเฉพาะเพื่อให้ผ่าน threshold
M4–M5 ใช้ error severity ที่ผู้รับผิดชอบงานยืนยันก่อน pilot; interface ผ่านอย่างเดียวไม่เปิด clinical action

## Change control

แก้ prompt/model/parser/preprocessing/tool/schema/policy ให้สร้าง config revision และประเมินผลกระทบ snapshot เก่าอ่านได้เสมอ Major contract changes ต้อง migration/compatibility tests; เปลี่ยนเพียงเอกสารไม่ต้อง re-run paid benchmark งานแรกและคำสั่งอยู่ BACKLOG/CODEX_HANDOFF

## v0.2 delivery mapping

M0 ต่อจาก baseline เป็น audit-hardened HTTP/contracts + frontend scaffold + deterministic Thai data fixtures. ส่วน M1 request validation/response contracts ได้ทำบางส่วนแล้ว แต่ framework migration, production auth, generic task binding และ browser acceptance ต้องดูสถานะจริงใน VALIDATION_REPORT. งานต่อใช้ B00R–B06R ใน BACKLOG ซึ่งแทนลำดับ B00–B11 เดิมสำหรับรอบรับช่วงนี้. ไม่เพิ่ม clinical scope หรือเปิด live inference.
