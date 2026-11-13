# Data staging and synthetic fixtures

ชุดนี้มี record fixtures ภาษาไทยแต่งใหม่ **18 กรณี** ไม่มีข้อมูลผู้ป่วยจริงและไม่มีการนำเข้า SQLite. `fixture-p-*` / `fixture-e-*` เป็นรหัสหน้าจอแบบ read-only; API runtime ยังคง `p-demo/e-demo/task-demo` ชุดเดียว.

## Reproduce and validate

จาก package root:

```bash
python scripts/generate_fixtures.py
python scripts/check_data.py
python contracts/check_contracts.py
```

Generator ใช้ seed `20261112`, version `1.0.0`, ไม่เรียก network/DB และได้ bytes เดิมทุกครั้ง. `check_data.py` ตรวจ checksum, reproducibility, unique IDs, staging boundary และ Draft 2020-12 fixture schema (ต้องมี jsonschema ตาม requirements-validation.txt). Contract checker ตรวจ frozen HTTP response fixture ด้วย schema ของ API แยกต่างหาก.

`data/fixtures/thai_records.json` เป็น **record + UI scenario specifications** ไม่ใช่ผลตอบ HTTP จริง; `expected_state` ไม่เพิ่ม enum ใน backend. `data/fixtures/api_response_index.json` เป็น index ไปยัง canonical `contracts/v1/fixtures/workflow.json`; ไม่สำเนาหรือดัดแปลง HTTP payloads เพื่อทำให้ UI ดูสำเร็จ. การเลือก frozen scenario ไม่ได้ทำ transaction.

Synthea FHIR R4 Sep2019 เป็น external candidate ที่ตรวจ official page, exact URL และ repository metadata แล้ว แต่ยัง **NOT_DOWNLOADED / NOT_BUNDLED** เพราะยังไม่ยืนยัน artifact-specific license/redistribution/training/third-party terminology conditions ได้จากหลักฐานที่อ่าน. ไม่สรุปว่าใช้งานไม่ได้ เพียงไม่อนุมาน Apache-2.0 ของ generator เป็น license ของ dataset. ไม่มี raw archive, FHIR patient หรือ Synthea-derived view model ใน ZIP นี้. ดู OPEN_DATA_MANIFEST และ evidence/SOURCE_REVIEW.md.

หากยืนยันเงื่อนไขของ artifact ได้ภายหลัง: ดาวน์โหลดจาก URL ใน manifest, เก็บ SHA-256 ของ bytes จริง, ตรวจ package metadata/terms, เลือก patient bundles 5–10 รายแบบ deterministic หลังจัดเรียงชื่อ resource, เก็บ selected IDs และ mapping lineage. ห้ามตั้ง retrieved_at/checksum จนดาวน์โหลดจริง. ยังไม่ import runtime จนมี migration และ scope tests สำหรับ multi-patient.

ข้อมูลแต่งใหม่ใช้เงื่อนไขใน licenses/AUTHORED_FIXTURES_CC0.md. ไม่ใช้ชุดนี้เป็น benchmark ทางคลินิกหรือหลักฐานลดขาดทุน.
