# POC-01: ตรวจความครบถ้วนเอกสารและเตรียมรายการให้ทบทวน

Version 0.1 · Administrative, synthetic demo selected first slice · Owner ทางผลิตภัณฑ์: solo owner · accountable domain professional: UNKNOWN

| หัวข้อ | ข้อกำหนด |
|---|---|
| ผู้ใช้ | เจ้าหน้าที่จัดเตรียมเอกสาร / reviewer |
| Domains | D01 D03 D10 D22 D34 D37 |
| เหตุผลจัดลำดับ | มี reference label ที่สร้างอย่างโปร่งใส; ใช้ shared core ครบโดยไม่พึ่ง hardware หรือ clinical model |
| Inputs | เอกสารข้อความสังเคราะห์ + expected checklist ที่มีรุ่น; patient/encounter และ source locator |
| Primary evaluator | exact missing-field set; evidence validity; unauthorized/stale/duplicate invariants |
| Comparators | deterministic checklist เป็น baseline; LLM-only/tools/agent ทดลองภายหลัง |
| ขอบเขตที่ไม่กล่าวอ้าง | ไม่มี lab interpretation, diagnosis, clinical recommendation หรือ signed record จริง |
| Acceptance | input version/permission/schema tests; 100% fixed engineering invariants; effectiveness ยังไม่ประเมิน |

## Contract และ review

ทุกคำขอมี purpose, patient/encounter, input versions, data class และ deadline ผลต้องระบุ outcome, evidence/source locator, model/config identity, limitations และ usage/cost ที่วัดได้ ไม่ทราบให้ null คง internal schema version และ specialist task contract ตามชนิดงาน ไม่ใช้ chat interface บังคับทุก service

สิทธิเริ่มต้นอ่าน context และสร้าง proposal เท่านั้น การบันทึกผลผ่าน reviewer ที่มี scope โดยผูก proposal/action version และ hash; recheck ก่อน commit การแก้ผลสร้างฉบับใหม่ หลักฐานเก่ายังตรวจได้

## Failure และทรัพยากร

missing/ambiguous/out-of-scope input ให้ abstain หรือ reject ตาม schema; timeout และ failure ลง ledger ทุกครั้ง ไม่มี silent fallback หากยังไม่มี live endpoint ใช้ mock ได้เฉพาะ explicit demo invocation ห้ามรายงานเป็น specialist result จริง

Cloud budget, latency target, concurrency, retention และ network ของ live route เป็น UNKNOWN ปิด paid route โดย default การหยุดเฉพาะ live integration ไม่หยุด contracts/fixtures/tests ใน sandbox

## Evaluation และการตัดสินใจ

ใช้ `evaluation/PROTOCOL.md`; fixed synthetic tests พิสูจน์ engineering behavior เท่านั้น ต้องมี representative dataset/reference labels และ reviewer evaluation ก่อนกล่าวอ้าง product/clinical effect เก็บ reviewer edits/rejections/time รวม failed attempts ด้วย ห้ามเลือกเฉพาะ success cases

เมื่อพบ cross-patient disclosure, unauthorized commit หรือ critical task error ให้หยุด route ที่เกี่ยวข้อง รักษาหลักฐานและ rollback config แก้ tests แล้วประเมินซ้ำ Domain-specific critical-error taxonomy ต้องให้เจ้าของงานยืนยันก่อน real pilot

แหล่งตั้งต้น: คู่มือ AI/data และ use-case/evaluation templates ในคลังที่แนบ; catalog เป็น navigation ไม่ใช่ clinical knowledge base ที่ผ่าน validation
