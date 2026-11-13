# HIS POC Starter 0.2.0

Thai-first AI-driven HIS/ERP engineering starter สำหรับ solo owner. มี shared core และ Champion candidates 4 งาน โดยทำ **document → evidence → proposal → human review → persisted result → audit** ด้วยข้อมูลสังเคราะห์และ explicit mock.

เริ่มรันที่ [START_HERE.md](START_HERE.md) · ส่งต่อด้วย [STARTER_PROMPT_TH.md](STARTER_PROMPT_TH.md) · ผลตรวจจริงใน [VALIDATION_REPORT.md](VALIDATION_REPORT.md)

## สิ่งที่เพิ่มในรุ่นนี้

- แก้ audit A01–A07: strict request validation, response contracts, document editor/retry, task scope และ persisted abstention reason
- React + TypeScript + Vite workspace ใน apps/web จาก official sidebar-01 พร้อม source/license provenance และ package lock
- Sidebar ครบ 38 domains; นอก first slice เป็น placeholder พร้อมสถานะตาม domain inventory
- Fixture mode แบบอ่านอย่างเดียวแยก API mode; record fixtures ภาษาไทย 18 กรณีและ frozen HTTP responses ตาม contract
- Additive migration สำหรับ runs.abstain_reason; singleton runtime เดิม ไม่เปิด multi-patient import

## โครงสร้าง

| Path | ใช้ทำอะไร |
|---|---|
| apps/web/ | frontend, typed adapters, tests, lockfile และ template provenance |
| src/his_poc/ | Python stdlib HTTP, strict boundary, SQLite service และ explicit mock |
| web/index.html | legacy demo reference ที่แก้ audit แล้ว |
| contracts/v1/ | 23 JSON schemas, OpenAPI และ frozen HTTP fixtures |
| data/ | authored fixtures, generator lineage, mapping, external source inventory และ notices |
| docs/DOMAIN_SCOPE.csv | ทั้ง 38 domains พร้อมสถานะ/ข้อจำกัด |
| docs/AUDIT_RESOLUTION.md | finding → fix → evidence |
| docs/MIGRATIONS.md | upgrade/rollback ของ synthetic DB |
| evidence/v0.2/ | ผลรันใหม่; evidence root เดิมเป็น historical v0.1 |
| GOAL.md / PLAN.md / BACKLOG.md | เป้าหมายและงานที่เดินต่อได้ |
| CODEX_HANDOFF.md / STARTER_PROMPT_TH.md | คำสั่งรับช่วงโดยไม่ต้องเขียน spec ใหม่ |

อ่าน source/template/data manifests ก่อนนำ third-party assets หรือข้อมูลไปใช้ต่อ. Exact checkpoints, endpoints, hardware, production identity และงบ HIS ยัง UNKNOWN. ไม่มี paid API, training, deployment, dr-train changes หรือ clinical validation ใน release นี้.
