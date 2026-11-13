# Workflows และความหมายของสถานะ

## POC-01 synthetic document completeness

| ขั้น | ผู้กระทำและข้อมูล | ข้อกำหนดที่ตรวจ | ผลที่เก็บ |
|---|---|---|---|
| Input | ผู้มีสิทธิเปิด patient/encounter และ document demo | authenticated actor, tenant/scope, strict body/metadata types และ optimistic input version (update_document ไม่กำหนดว่า encounter ต้อง open) | document/task reference |
| Evidence | backend/tool อ่าน document ที่ได้รับสิทธิ | patient/encounter สอดคล้อง; source/version/locator | immutable input snapshot ของ proposal |
| Proposal | explicit mock adapter ตรวจ checklist demo | data class synthetic, configured profile, output contract | structured draft + run outcome/latency/cost |
| Review | reviewer เห็น evidence และ action ที่จะบันทึก | version/action hash, current permission; edit ต้องเป็นฉบับใหม่ | review decision/edits/reason |
| Persist | backend commit ใน transaction | recheck context/status/input versions/approval expiry and hash; idempotency | result หนึ่งรายการและ audit ที่ผูกกัน |
| Audit | authorized viewer อ่าน trace | scope ก่อนคืนข้อมูล; ไม่มี credential ใน response | actor/time/action/reference และ outcome |

ชื่อ field/route/state ที่ executable ใช้จริงอยู่ `API_IMPLEMENTATION.md` และ versioned contracts เอกสารนี้อธิบาย invariants ห้ามสร้าง endpoint ใหม่จากชื่อขั้นในตารางโดยไม่แก้ contract

Proposal ยังไม่ใช่ผลรับรอง การแก้ payload หลัง review ทำให้ approval เดิมใช้ไม่ได้ การ reject ไม่สร้าง result การ commit ผ่านหมายถึงบันทึกผลตรวจเอกสาร demo ในฐานข้อมูลเท่านั้น ไม่หมายถึงแพทย์ลงนามเวชระเบียนหรือส่งข้อมูลสู่ระบบจริงแล้ว

## Runtime รุ่นนี้ที่ทำจริง

Seed เป็น `p-demo/e-demo/d-demo/task-demo` โดย `reviewer-demo` มีสิทธิ synthetic-only; ไม่มี patient/user CRUD หรือ production identity. Proposal มีสถานะ `pending → approved/rejected` และ `approved → committed`; reviewer edit เพิ่ม version/hash และคง pending เพื่อให้ approve ฉบับใหม่ อายุ proposal 900 วินาทีจากเวลาสร้าง การ cancel ทาง transport ยังไม่ implement

Snapshot มี encounter version, document ID/version/hash, locator `document.content` และ data class; immutable proposal_versions เก็บ action แต่ละฉบับ การ commit ใช้ SQLite transaction เดียวสำหรับ result, task completion, idempotency และ audit Same-key replay ตรวจสิทธิ caller ปัจจุบันแต่ไม่สร้าง write ใหม่จึงไม่ตรวจ context ซ้ำแบบ new commit

Timeout/failure/invalid/abstain เป็นการจำลองของ mock การ latency ที่เก็บเป็นเวลารัน harness จริง ส่วน usage/cost เป็น null ยังไม่มี real timeout/cancellation, remote adapter, external write, clinical signature หรือ production restore ผล HTTP 200 ของ AI request อาจมี outcome failure ได้ client ต้องอ่าน outcome ไม่ใช้ HTTP status เพียงอย่างเดียว

## Exception table

ตารางนี้รวมทั้ง behavior ที่ implement และ target requirement; cancellation/transport retry/reconciliation ภายนอกยัง planned ตาม API_IMPLEMENTATION และ BACKLOG


| เหตุการณ์ | พฤติกรรมที่ต้องได้ | วิธีทำงานต่อ |
|---|---|---|
| actor ไม่มีสิทธิ/ข้าม patient หรือ encounter | ปฏิเสธก่อนอ่าน/ใช้ข้อมูล; tool ตรวจซ้ำ | ผู้มีสิทธิเปิดงานที่ถูกต้อง |
| provider timeout/error/schema invalid | run ไม่เป็น success; เก็บ outcome/latency/error ที่ปลอดภัย | retry แบบขอบเขตเดิมหรือคนทำต่อ; ไม่มี silent mock |
| insufficient evidence / abstention | ไม่สร้างผลรับรองอัตโนมัติ | เพิ่มหลักฐานแล้วสร้าง proposal ใหม่ |
| reviewer edits | เก็บผลก่อนแก้และฉบับใหม่; ต้อง review ฉบับใหม่ | ตรวจใหม่และอนุมัติ version/hash ใหม่นั้น |
| input หรือ encounter เปลี่ยนหลัง review | commit ปฏิเสธ stale | สร้าง proposal จาก current snapshot และ review ใหม่ |
| cancelled/expired approval | commit ปฏิเสธ | เปิด workflow ใหม่ตามสิทธิ; ห้าม revive ด้วย retry |
| retry key + same approved payload | คืนผลเดิมเมื่อยังมีสิทธิ; ไม่ insert ซ้ำ | client reconcile จาก result ID |
| retry key + changed payload | conflict | ใช้ key ใหม่ได้หลังอนุมัติ payload ใหม่เท่านั้น |
| crash/unknown response | ตรวจ idempotency/result ด้วยบริบทเดิม | ห้ามเดาว่าไม่สำเร็จแล้วลงซ้ำ |

## Specialist workflows ที่ยังเป็น integration-planned

DR: authorized image reference → modality/quality/preprocessing check → specialist inference → task-specific output → reviewer → bounded referral/follow-up task ตาม intended use ค่า grading และภาพต้นฉบับไม่ถูก LLM เขียนทับ; retained evidence รวม artifact/model/preprocessing version และ laterality

CAD: validated feature set/time horizon → missingness/OOD checks → specialist risk estimate → reviewer เห็น calibration/use limitations → persisted reviewed assessment ไม่มีการเปลี่ยน risk score เป็น diagnosis หรือ treatment order อัตโนมัติ

Claim completeness: encounter/service evidence + payer rule snapshot → deterministic completeness baseline → optional evidence-grounded draft → coder/reviewer → correction task การ submit claim/acknowledgement/approved amount/remittance เป็นขั้นต่างหากและยังไม่ implement

## Data ownership และธุรกรรมข้ามระบบ

patient/encounter demo เป็นเจ้าของโดย starter; production system of record ต้องตกลงเมื่อมีคู่เชื่อมจริง Document source revisions เป็นหลักฐานและผล review เป็น record คนละชนิด ผลแก้ไขต้อง preserve provenance สำหรับ external writes ในอนาคตใช้ local transaction + outbox + downstream idempotency + reconciliation; ปุ่มส่งไม่เท่ากับปลายทางรับแล้ว Starter ยังไม่มี external writes/outbox worker

## Singleton task และ frontend v0.2

ตรวจ target p-demo/e-demo/task-demo ก่อน/หลัง inference, review และ first commit. Commit ปิดเฉพาะ task-demo ไม่ปิดทุก task ใน encounter. Task completed/cancelled/deleted ไม่ถูก reopen เมื่อ restart; หลัง completed ให้ใช้ DB path ใหม่สำหรับ journey ใหม่. Same-key authorized replay ยังคืนผลเดิม. การแก้ document ยังตรวจ scope/version แต่ไม่ได้ reopen task.

Abstention reason ถูกเก็บทั้ง response/runs/audit (ไม่เกิน 1000 ตัวอักษร; แถวก่อน migration เป็น null). Frontend ใหม่แยก API mode จาก read-only fixture mode; การเลือก fixture/frozen state ไม่ทำ transaction. การ parse JSON-string fields อยู่ typed adapter; dirty document ใช้ baseline version เดิมจนบันทึกหรือทิ้งร่างโดยชัดเจน.
