# การตรวจแหล่งอ้างอิงสำหรับ starter

ตรวจวันที่ 12 พฤศจิกายน 2569 (2026-11-12) เอกสารนี้แยกสิ่งที่อ่านจริงในรอบสร้าง starter ออกจากสถานะที่ชุดอ้างอิงเดิมรายงานไว้

## ขอบเขตการอ่าน

- `source_catalog.json`: parse รายการ metadata 94 แหล่งและอ่าน ID ชื่อ URL และข้อจำกัด ไม่ได้เปิดอ่านต้นฉบับทั้ง 94 แหล่ง สถานะ verified/downloaded ในต้นฉบับเป็นรายงานของแพ็กเกจเดิม
- อ่านคู่มือภาพรวม AI architecture และ data/interoperability/ledger เป็นบริบทออกแบบ ไม่ถือเป็นข้อกำหนดโรงพยาบาลหรือกฎ payer ที่ยืนยันแล้ว
- SAFER Patient Identification: อ่านข้อความ PDF หน้า 1–3 และ 6–7 โดยเน้น checklist; ไม่ตรวจทุกหน้าและไม่ได้ตรวจ layout
- NIST AI RMF 1.0: อ่านข้อความ PDF หน้า 27–28 และ 34–35 (เลขหน้าพิมพ์ 22–23, 29–30) เน้น inventory, human/AI responsibilities และ documented evaluation
- `deep-research-report.md`: อ่านเฉพาะบรรทัด 1–33 และ 795–850 เป็นประวัติแนวคิด PharmaCore; ไม่ resolve citation tokens เดิม และไม่ใช้คำแนะนำ fresh repository เดิมตัดสินแทนการตรวจ repository ปัจจุบัน

## แหล่งโมเดลทางการที่เปิดตรวจใหม่

| ID | แหล่ง | สิ่งที่ใช้ตัดสินใจ | ข้อจำกัด |
|---|---|---|---|
| RT01 | [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B) | มีโหมด thinking/non-thinking และการแยก reasoning จาก final content | เป็น candidate เท่านั้น; ไม่ตรึง revision และไม่ได้รัน endpoint |
| RT02 | [Typhoon2.5-Qwen3-4B model card](https://huggingface.co/typhoon-ai/typhoon2.5-qwen3-4b) | ตัวอย่าง serving/tool ใช้ Hermes parser; namespace ในบางตัวอย่างยังเป็น scb10x | ห้ามคัด command ไปใช้โดยไม่ตรวจ artifact และ engine version; ไม่ใช่การเลือก 4B แทนเจ้าของ |
| RT04 | [MedGemma model card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card) | หน้า 1.5 ระบุ 4B multimodal IT และข้อจำกัด multi-turn; ใช้เป็น bounded specialist task candidate | มีข้อความ modality ใหม่กับข้อจำกัด single-image ที่ต้องตีความรายงาน; ห้ามเหมารวม multi-image หรือ clinical effectiveness |

ชื่อเหล่านี้อธิบาย candidate จากชุดส่งต่อ ไม่เติม exact checkpoint ใน inventory ของ Qwen 8B, Typhoon หรือ MedGemma ที่เจ้าของยังไม่ยืนยัน การอ่าน model card ทำให้รู้ declared capability เท่านั้น ไม่ใช่ verified capability ของ endpoint ใด

## ข้อสรุปสำหรับการออกแบบ

SAFER Patient Identification หน้า 6–7 ใช้สนับสนุนการคงตัวตนผู้ป่วยในบริบทงานและการติดตามข้อผิดพลาด ไม่ใช่หลักฐานว่า synthetic demo มีระบบ EMPI หรือ workflow ระบุตัวผู้ป่วยจริงครบแล้ว แหล่ง: [SAFER Guides](https://healthit.gov/clinical-quality-and-safety/safer-guides/).

NIST AI RMF 1.0 ส่วน GOVERN และ MEASURE ใช้สนับสนุน inventory ที่ตามรอยได้ การแบ่งหน้าที่คน/AI และการบันทึก test set, metrics, limitations การตรวจ endpoint จึงแยกจาก task/clinical/product evaluation แหล่ง: [NIST AI RMF](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10).

ข้อกำหนดเรื่อง transaction/version/idempotency และ policy ใน starter เป็นข้อกำหนดวิศวกรรมของโครงการ ไม่อ้างว่า framework เหล่านี้กำหนด schema หรือ threshold เดียวกัน รายละเอียดกำกับดูแล กฎหมายไทย payer schema และ clinical rules ต้องตรวจแหล่งปัจจุบันเฉพาะงานก่อนนำไปใช้จริง; starter ไม่สร้างข้อสรุปใหม่ด้านกฎหมายหรือการรักษา

## NOT_RUN / UNKNOWN

- ไม่ดาวน์โหลด model weights ไม่เรียก live API และไม่เชื่อม dr-train
- ไม่ยืนยัน hardware, endpoint, model revision, license acceptance หรือค่า inference ของบัญชีผู้ใช้
- ไม่อ่าน PDF ทั้ง 25 ฉบับและไม่ตรวจซ้ำ URL ของ catalog ทั้ง 94 แหล่ง
- ไม่ประเมิน clinical accuracy, clinical safety, reimbursement correctness หรือผลกำไรจากเดโม

รายละเอียดระดับไฟล์และ hashes ให้ดู `INPUT_MANIFEST.md` / `SOURCE_REGISTER.json`; รายงานนี้ไม่เพิ่มสถานะ PASS ให้ runtime
