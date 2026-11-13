# Evaluation protocol v0.1

สถานะ: engineering fixtures พร้อม; model/product/clinical comparison **NOT_RUN**. ไม่มี benchmark score ในชุดนี้ Fixed corpus `cases.jsonl` เป็น synthetic specification ของสถานการณ์ ไม่ใช่ไฟล์ที่ regression runner โหลดโดยอัตโนมัติ; executable tests อยู่ `tests/` และผลจริงอยู่ VALIDATION_REPORT

## คำถามและหน่วยวิเคราะห์

POC-01: ระบบค้นสิ่งที่ขาดและสร้าง proposal ที่อ้างหลักฐานถูกต้องได้หรือไม่ โดยรักษาสิทธิและความถูกต้องของธุรกรรม หน่วยคือ encounter/document case หนึ่งชุด; reruns ของ case เดียวไม่เป็นตัวอย่างอิสระ เป้าหมายหลัง integration คือเปรียบเทียบคุณภาพและภาระตรวจต่อ case ไม่อ้างผลทางคลินิก

## Arms และ fairness

| Arm | การทำงาน | สิ่งที่ต้องตรึง |
|---|---|---|
| A deterministic | checklist/rules + same allowed evidence | rule version และ labels |
| B LLM-only | normalized evidence ใน context ไม่มี tools | model/checkpoint/prompt/token budget |
| C LLM+tools | same model + bounded read tools; fixed orchestration | tool allowlist, evidence pool และ max calls |
| D proposed agent | adaptive bounded tool selection ถ้ามีเหตุผล | same model/data/tools/budget; orchestration เป็นตัวแปร |

Mock เป็น harness ไม่ใช่แขน LLM และไม่ได้พิสูจน์ว่า D ดีกว่า A–C. ถ้ายังไม่ implement D ไม่ต้องสร้างผลจำลองมาเติม การเปรียบเทียบ DR/CAD ใช้ specialist baselines ตามใบ POC ไม่บังคับสี่แขนนี้กับ image classifier หรือ risk model

## Dataset/reference และการตรึง

เริ่ม 12 cases สังเคราะห์ใน cases.jsonl สำหรับ implementation planning และ adversarial requirements แยกจาก seed UI หนึ่ง journey ที่ runtime ใช้ แหล่งคือผู้จัดทำ starter ไม่มีข้อมูลบุคคลจริง ไม่มีการดึงเอกสาร 94 แหล่งเข้า patient RAG กำหนด labels/expected state แบบ deterministic ก่อน model run

ก่อน comparative run ขยายจำนวนจาก desired precision ตาม outcome; sample size และ clinical reference reviewers ยัง UNKNOWN. แยก development/calibration/test ด้วย patient และ source-template family; ป้องกัน near-duplicate templates ข้าม split ไม่มีการใช้ test labels ปรับ prompt ถ้าทำให้เปลี่ยน protocol version และรายงาน deviation

Freeze corpus SHA-256, rule/schema/prompt/config/tool revision, model artifact/runtime, seed/generation settings และ evaluator hash. `fixtures_manifest.json` ผูก bytes ของ cases.jsonl รุ่นนี้ ไม่ใช่การลงทะเบียน clinical study

## Rubric

1. Correct issue set: exact-match ต่อ case และ issue precision/recall; no-positive cases รายงาน exact-match และ FP count ไม่แปลง undefined precision เป็น 1 เงียบ ๆ
2. Evidence: ทุก issue มี permitted source/version/locator ที่ resolve ได้; wrong-patient evidence เป็น critical error
3. Transaction: unauthorized/stale/changed-payload retry ต้องถูกปฏิเสธ; same request retry ไม่มี duplicate result
4. Unsupported claims/omissions: นับต่อ case และระบุ severity; clinical severity rubric ยังต้อง adjudication
5. End-to-end outcome: success, error, timeout, abstained, cancelled แยกกัน เก็บทุก eligible case และทุก attempt
6. Human review: reject/edit/accept, edit diff, review duration และ post-review errors; ไม่ใช้ปุ่ม approve เป็นหลักฐาน effectiveness
7. Resources: wall latency, measured usage, currency/cost source; unknown usage/cost = null ไม่ใช่ศูนย์; mock paid API cost zero ได้เฉพาะเพราะไม่มี external paid call และยังไม่ใช่ต้นทุน compute รวม

## การวิเคราะห์และเกณฑ์จบ

Engineering acceptance: executable invariant tests ที่ implement ต้องผ่านทั้งหมด ไม่มี cross-patient write, duplicate committed result หรือ stale approval accepted ในชุดทดสอบ เกณฑ์นี้เป็นเงื่อนไขส่งต่อโค้ด ไม่ใช่อัตราความปลอดภัยในประชากรจริง

Comparative evaluation: รายงาน paired per-case differences, distributions และ uncertainty ที่จัดกลุ่มตาม case/patient; ไม่ใช้จำนวน retries เพิ่ม n ผลบน synthetic เป็น exploratory เท่านั้น ก่อน frozen representative evaluation กำหนด primary metric และ minimum worthwhile improvement ตาม workflow cost/reviewer burden เกณฑ์ตัวเลข effectiveness ตอนนี้ UNKNOWN

Go M2 = integration/capability checks ผ่านและ authorization ครบ. Go M3 = corpus/evaluator frozen และทุก eligible run ถูกเก็บ. Go pilot ต้อง independent intended-use evidence และ owner domain decision ไม่ใช้ H01–R07 แทน clinical acceptance. Hold/inconclusive เป็นผลที่ถูกต้องเมื่อข้อมูล/CI ไม่พอ

## Financial outcomes สำหรับ POC-03

| ตัวแปร | ความหมาย | ห้ามใช้แทน |
|---|---|---|
| service cost | ต้นทุนตาม cost allocation version | ราคาคิดค่าบริการ |
| billed amount | ค่าบริการเรียกเก็บ | ยอด claim ที่ส่ง |
| claim submitted | ยอดตามรุ่น claim ที่ส่งจริง | payer-approved amount |
| payer approved | ยอดอนุมัติหลัง adjudication | เงินรับเข้าจริง |
| cash received | เงินรับที่ reconcile กับ statement | รายได้ทั้งหมด/กำไรโดยอัตโนมัติ |
| receivable balance | ยอดลูกหนี้หลัง postings/adjustments | claim completeness rate |

ทุกยอดมี currency, source transaction, effective date และ version ใช้ decimal precision ตาม payer/finance policy ที่ยืนยันภายหลัง อย่านับ claim resubmission เป็นรายได้ใหม่ การลดเวลาและ completeness gain ต้องรายงานแยกจาก cash outcomes
