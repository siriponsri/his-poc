# POC-02: ผลคัดกรองจอประสาทตาและงานส่งต่อ

Version 0.1 · Candidate, integration-planned · Owner ทางผลิตภัณฑ์: solo owner · accountable domain professional: UNKNOWN

| หัวข้อ | ข้อกำหนด |
|---|---|
| ผู้ใช้ | ผู้ตรวจคัดกรอง / จักษุแพทย์ผู้ทบทวน |
| Domains | D11 D20 D22 D37 |
| เหตุผลจัดลำดับ | มีบริบท DR เดิมแต่ current service/artifacts ยังต้องตรวจ; reuse specialist ผ่าน contract แยก |
| Inputs | ภาพที่มีสิทธิใช้, patient/laterality, modality/device, image-quality reference, grading labels, referral rule version |
| Primary evaluator | sensitivity/specificity at frozen threshold, gradability/abstention, patient-level confidence intervals; workflow follow-up completion |
| Comparators | specialist baseline เทียบ candidate เดิมบนภาพเดียวกัน; LLM ใช้เฉพาะ drafting และประเมินแยก |
| ขอบเขตที่ไม่กล่าวอ้าง | ไม่แทน specialist ด้วย medical LLM; ไม่ยืนยัน clinical validity จาก smoke test |
| Acceptance | แบ่ง patient/site/device ไม่รั่ว; freeze preprocessing+artifact+threshold; clinical threshold/sample size UNKNOWN |

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
