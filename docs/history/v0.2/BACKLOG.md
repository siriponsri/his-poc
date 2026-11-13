# Backlog v0.2.0 — ordered executable work

A01–A07 audit ถูกแก้ใน release นี้; หลักฐาน current run อยู่ VALIDATION_REPORT. งาน B00R–B06R แทนลำดับเดิม ไม่ถือ B01 framework migration เสร็จจาก request validator เพียงอย่างเดียว.

| ID | Input และผลลัพธ์ | Files / งาน | Acceptance | Dependencies |
|---|---|---|---|---|
| B00R | รับ baseline และตรวจ browser จริง | START_HERE, scripts, apps/web/tests, evidence | hash + Python/schema/legacyJS + npm ci/typecheck/build/test; browser edit→approve→commit→reload/audit, fixture no-write, stale/forbidden/retry; รายงาน NOT_RUN เฉพาะที่ทำไม่ได้ | ZIP + Python/Node; ไม่ต้องมี model |
| B01R | ย้าย HTTP transport สู่ framework ที่ดูแลต่อได้ | src/his_poc/server.py, request_validation, tests, dependency lock | คง v1 wire shape/status, 176 parity suite และ frozen responses; negative cases ไม่ mutate; UI adapter ผ่าน; เลือก/pin supported framework จากเอกสารจริง | B00R; ไม่เปลี่ยน auth server/deploy |
| B02R | Identity / actor-permissions read model | versioned contract + backend/frontend adapter | server เป็นผู้ตรวจสิทธิ; UI ไม่เดาสิทธิจาก token; revoked reviewer/cross tenant/patient fail; session switch ไม่มี stale selection/draft | B01R; IdP จริงรอ authorization |
| B03R | Persisted proposal→task binding + migrations | DB migrations, service, contracts, fixtures | task version/status binding, scope tests, multiple tasks ไม่ปิดข้ามกัน, old DB upgrade/rollback; generic patient/encounter auth ก่อน import | B01R/B02R |
| B04R | Document history/amendment และ operational integrity | immutable document versions, audit denial events, backup/restore | stale context/review audit reconstructable; restore drill IDs/hashes/relations; signed records แยก amendment | B03R |
| B05R | One actual inference integration | inventory/model registry, native adapter, capability/policy/budget | exact artifact/engine/parser/config, endpoint identity, schema/unsupported modalities, timeout/cancel/usage, all attempts retained; integration แยก quality | hardware/endpoint/authorized resources; paid budget ถ้าจำเป็น |
| B06R | Task-specific evaluation และ POC ถัดไป | evaluation/, pocs/, specialist contracts | baseline vs LLM-only/tools/agent; paired outcomes incl failure/cost/edit; DR/CAD evaluator ของตัวเอง; claim completeness ไม่ใช่ profit | B05R สำหรับ model arms; deterministic ทำก่อน |

## First concrete coding task

ทำ B00R บนเครื่อง Codex แล้วเริ่ม B01R: pin Python framework, ห่อ service เดิมด้วย validated request DTO/error mapping และรักษา atomic review/commit semantics. ไม่ปรับ data class, provider routes หรือเพิ่ม patient seed เพื่อทำ demo ให้ดูใหญ่ขึ้น. ทดสอบ backend และ frontend adapter ร่วมกันหลังเปลี่ยน transport.

## สิ่งที่ไม่บล็อกทั้งโครงการ

UNKNOWN dr-train/model/endpoints/budget บล็อก B05R live ส่วน B00R–B04R ทำ offline ต่อได้. Synthea license/terms ที่ยังไม่ยืนยันบล็อกการ bundle artifact นั้น ส่วน authored fixture/data mapping ทำต่อได้. Hospital/payer SOP ที่ขาดบล็อกการอ้าง compliance/clinical effectiveness ไม่บล็อก generic synthetic completeness.
