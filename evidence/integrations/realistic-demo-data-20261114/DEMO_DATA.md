# CareBalance fictional demonstration cohort

All names, dates of birth, histories, vital signs and lab values in this cohort
were authored for the POC. No record represents a real person. The numeric HN
values belong to the CAREBALANCE_DEMO issuer. The global Demo notice remains.
Reference intervals are illustrative authored text, not validated clinical rules.

ข้อมูลทั้งหมดในชุดนี้แต่งขึ้นสำหรับสาธิต ไม่ใช่ข้อมูลผู้ป่วยจริง ใช้ชื่อและค่า
ตัวอย่างที่อ่านเหมือนเวชระเบียนเพื่อให้ทดลองงานได้สะดวก อายุด้านล่างคำนวณจาก
วันเกิดที่บันทึก ณ 14 พฤศจิกายน2026 โดยไม่บันทึกอายุเป็นค่าคงที่

| Demo HN | Invented full name / นามสมมุติ | Age | Sex | Consultation / ตัวอย่างการตรวจ |
| --- | --- | ---: | --- | --- |
| 6901425 | สุเมธ ภัทรกุล | 58 | Male / ชาย | ติดตามเบาหวาน |
| 6901426 | อรอนงค์ วัฒนธารา | 61 | Female / หญิง | ติดตามความดันโลหิต |
| 6901427 | ภาคิน พงศ์ธนกิจ | 36 | Male / ชาย | ทบทวนผลตรวจสุขภาพ |
| 6901428 | ปาริฉัตร กิตติธารา | 47 | Female / หญิง | ติดตามอาการอ่อนเพลีย |
| 6901429 | สมภพ ธีรวัฒน์ | 68 | Male / ชาย | ติดตามเบาหวานและการทำงานของไต |
| 6901430 | รินรดา สุวรรณเมธา | 29 | Female / หญิง | ทบทวนผลเลือดหลังอาการอ่อนเพลียดีขึ้น |

Six new patients have six OPD visits, six draft consultation notes and eleven
released typed D10 lab sources. A total of23 new tasks comprises eleven completed
lab acquisition tasks and twelve OPEN review tasks: six document reviews and
six LabClear reviews. These are distinct task states and should not be reported
as23 open tasks. The normal API batch executed146 mutations once.

Four existing seeded patients received only invented display names and version
increments1→2 through audited Patient PATCH. Existing DOB/sex/status/identifiers
were retained. They retain unknown sex and legacy SYN identifiers where present;
the UI must not infer missing sex or invent a new numeric HN for those records.
The exact four row exceptions appear in production-verification.json.

ผู้ป่วยใหม่ทั้ง6รายมี Encounter เอกสารการตรวจ และผล Lab พร้อมงานให้ทดลองทบทวน
ส่วน Vital signs, น้ำหนัก ส่วนสูง และBMI อยู่ในข้อความเอกสาร ระบบไม่ได้เพิ่ม
โมดูลวัดสัญญาณชีพแบบมีโครงสร้าง ยังรอผู้ตรวจทบทวนประวัติยาและการแพ้ยา
ไม่มีการแต่งชื่อแพทย์แล้วแสดงว่าเป็นผู้ลงนามจริง

Existing test01 care scope was expanded only to the six new patients; the
original patient-001 assignment remains. No password, membership, role,
credential, DR grading grant or signing grant changed. The operator used normal
role accounts and new own CLI sessions with CSRF and durable idempotency keys.
This public package contains no credentials, cookies, full row inventories or
the private authentication/dispatch ledger.

Actual PostgreSQL readback confirms all old nonpatient rows and source files
were retained, with only the four approved Patient name/version exceptions.
All9 existing AI inferences and9 committed results remain. Separate DR and
LabClear database rows and all three app container/image identities stayed
unchanged. No new AI/model call, DR transfer, LabClear import/confirmation,
receiver write, seed/reset/migration or direct SQL mutation occurred.
The owner-held renamed MMRDR images remain untouched pending eye metadata.

Production database/API qualification passed; public browser acceptance is
recorded separately and is NOT_RUN in these receipts. Clinical accuracy or
effectiveness was not evaluated. Authored-cohort.json is data documentation,
not an automatic runtime seed or startup instruction.

## Evidence retained

- production-verification.json: safe provenance, all six patient/encounter IDs,
  six document/revision IDs, eleven lab/order/acquisition-task IDs, twelve review
  task IDs, four normal API audit records, hashes and preservation checks.
- verification-after.json: safe preservation summary and exact name/version
  amendments, excluding raw table inventories.
- offline-validation.json: actual DTO schemas and fake-transport cookie/auth/me,
  durable-ledger, unknown-outcome stop and receipt-cache checks.
- postgresql-rehearsal.json and corrected-v2 XML/log: one actual disposable
  PostgreSQL18 case executing146 planned normal API mutations, with one same-key
  replay check. This is separate from production readback evidence.
- Initial rehearsal XML/log is retained: independently seeded creation timestamps
  differed from production. The first case failed before cohort API dispatch;
  demographic/context/version equivalence was corrected and the bounded rerun
  passed. The initial PowerShell wrapper exit code did not propagate; the
  failing XML/log remains authoritative. The corrected wrapper recorded exit0.

No additional model run or clinical review is implied by a released authored
lab result. Users still perform the existing document-AI, LabClear and DR review
workflows explicitly.

Public initial XML redacts a credential-field label in embedded fixture source. No actual credential value was present; original initial XML remains private. The first staging attempt stopped on this conservative field-name scan; no production write occurred.
