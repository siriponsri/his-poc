# POC-03: ความพร้อมเอกสารเคลมและติดตามการแก้ไข

Version 0.1 · Candidate, integration-planned · Owner ทางผลิตภัณฑ์: solo owner · accountable domain professional: UNKNOWN

| หัวข้อ | ข้อกำหนด |
|---|---|
| ผู้ใช้ | เวชระเบียน / coder / เจ้าหน้าที่รายได้ |
| Domains | D23 D24 D26 D35 D37 |
| เหตุผลจัดลำดับ | ตอบโจทย์รายได้และวัดงานได้ แต่ต้องแยก completeness จากยอดอนุมัติและเงินจริง |
| Inputs | synthetic encounter/service/charge + payer schema/rule version; production rule owner UNKNOWN |
| Primary evaluator | issue precision/recall, false alerts, correction time; later rejected/approved/received amounts independently |
| Comparators | deterministic payer rules; optional LLM text evidence extraction; tool/agent arms same data/budget |
| ขอบเขตที่ไม่กล่าวอ้าง | ไม่ส่ง claim, เปลี่ยน diagnosis code หรือรับรอง eligibility อัตโนมัติ |
| Acceptance | rule version frozen; financial totals reconcile separately; baseline completeness gain ไม่ใช่กำไร |

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
