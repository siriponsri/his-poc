# Audit resolution — v0.2.0

Input: WORK_NEXT_PROMPT_TH.md และ HIS_POC_Audit_and_Work_Brief_2026-11-12.zip. ใช้ baseline ZIP v0.1.0 hash `41597ff6accc9951e252221b0b657a55eeae71646fc5501f176e477928da859c` แตกสำเนาแยก; ต้นฉบับไม่เปลี่ยน. ตรวจ candidate diff, before/after hashes และ git apply --check ก่อนใช้. หลักฐานรอบนี้อยู่ evidence/v0.2 ไม่ใช้ PASS จาก audit pack แทนการรันใหม่.

| Finding | การแก้ | หลักฐานหลัก |
|---|---|---|
| A01 malformed request/mutation | stdlib request validator ก่อน dispatch, strict JSON parsing, content headers/body size, positive integer normalization ไม่รับ bool, nested fields/hash/edits | tests/test_http_contracts.py และ request/schema parity |
| A02 incomplete response contracts | เพิ่ม health/context/propose/review/document-update responses, OpenAPI response references, actual HTTP frozen fixtures | contracts/check_contracts.py และ contracts/v1/fixtures/workflow.json |
| A03 document overwrite | legacy hydrate editor, preserve metadata/dirty baseline version; React editor ทำตาม invariant เดียวกัน | tests/test_frontend_behavior.js และ apps/web tests |
| A04 errors/stale UI/retry | visible errors, reconcile selected proposal, same payload/key retry, disable pending duplicate, explicit unknown commit outcome | legacy behavior tests และ frontend tests |
| A05 approve with edits ambiguity | edits allowed only edit; approve/reject reject property; edit creates new version needing review | service/HTTP/schema tests |
| A06 all tasks closed | update target task-demo only; verify singleton target lifecycle; restart ไม่คืน task ที่ลบ/ปิด | tests/test_service_regressions.py |
| A07 abstention lost | additive runs.abstain_reason migration; response/context/audit retain bounded reason; old rows null | migration and abstention regressions |

## ขอบเขตที่ยังคงไว้

Singleton patient/encounter/task เดิม ไม่เพิ่ม multi-patient seed. Task completed แล้วไม่สร้าง proposal ใหม่; same-key authorized replay คืนผลเดิม. Generic proposal→task binding ยังเป็นงานต่อ. Stdlib HTTP ยังเป็น local demo; framework migration ไม่ได้จบเพียงเพราะ audit patch ผ่าน.

Legacy JS tests เป็น DOM/fetch doubles ไม่ใช่ browser. Frontend typecheck/build และ adapter tests ไม่แทน browser interaction/visual QA. จำนวนและสถานะที่รันใหม่ดู VALIDATION_REPORT.md; อย่านำ candidate count มาเป็นเป้าหมายบังคับ.
