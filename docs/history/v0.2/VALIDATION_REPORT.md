# Validation report — HIS POC v0.2.0

วันที่ตรวจ 2026-11-12. ผลต่อไปนี้มาจากการรันรอบแก้ audit ไม่ใช้ผลใน audit kit แทน current execution. ทดสอบด้วย synthetic data และ explicit mock เท่านั้น; ไม่มี paid API, training, deployment, live model หรือ server changes.

## Baseline และ patch integration

- เก็บ ZIP v0.1.0 เดิมไว้; แตกสำเนาแยกใน revision/HIS_POC_Starter.
- Baseline ที่ทำซ้ำ: 22 Python tests, 18 schemas และ 82 file hashes ผ่าน.
- ตรวจก่อน/หลังของ candidate overlay18ไฟล์ตรง manifest, `git apply --check` ผ่าน แล้ว apply จริง.
- Command/exit/environment: `evidence/v0.2/hardening-execution.json`. Baseline ZIP SHA256 `41597ff6accc9951e252221b0b657a55eeae71646fc5501f176e477928da859c`.

## ผลตรวจใหม่

| Check | ผลจริง / ขอบเขต | หลักฐานและคำสั่ง |
|---|---|---|
| Backend regression | 45 Python tests PASS รวม strict request, bool/integral version, no mutation on invalid body, task guards, migration, expiry/stale/idempotent retry/permission/failure retention | evidence/v0.2/hardening-tests.txt; `python -m unittest discover -s tests -v` |
| Legacy UI behavior | 12 tests PASS ใช้ actual JS กับ DOM/fetch doubles | evidence/v0.2/legacy-ui-behavior.txt; `node --test tests/test_frontend_behavior.js` |
| Contract validation | 23 schema definitions, 2 examples, 176 request/schema parity cases, 27 fresh local HTTP responses และ 27 frozen responses PASS | evidence/v0.2/hardening-contracts.txt; `python contracts/check_contracts.py` |
| New frontend | 17 typed adapter/state tests และ TypeScript typecheck PASS; production build PASS จาก locked dependencies | apps/web/evidence/ และคำสั่งใน apps/web/README.md |
| Data | 18 authored Thai record fixtures; schema, deterministic regeneration, hashes, canonical API response index27 และ staging-boundary checks PASS | data/evidence/check_data.json; `python scripts/check_data.py` |
| Package consistency | required docs,38 domain IDs,JSON/ref/link checks, mock/live policy, canonical copies ของ domain/data/API fixtures | evidence/v0.2/package-check.txt; `python scripts/check_package.py` |
| Independent review | อ่าน code/contracts/data/UI และทำ checks ซ้ำ; แก้ findings ก่อนส่ง | evidence/v0.2/independent-review.md |

Core runtime Python3.12.14 / SQLite3.53.1; Node24.22.1 และ jsonschema4.26.0 ในรอบนี้. Frontend dependency versions ใช้ package-lock.json และ TEMPLATE_PROVENANCE.json เป็นหลัก ไม่ใช่การเดาเวอร์ชัน. ล็อก validation tooling แยก requirements-validation.txt.

## Findings ที่ปิดใน release

A01–A07 mapping อยู่ docs/AUDIT_RESOLUTION.md. เพิ่ม correction จาก independent frontend review:

- Reviewer draft ผูก version/hash ที่เริ่มแก้ ไม่ adopt รุ่นที่ refresh ใหม่เงียบ ๆ; stale edit ถูก server ปฏิเสธและต้อง discard/rebase โดยชัดเจน.
- Failed proposal ไม่ auto-select ข้อเสนอสำเร็จเก่าเหมือนเป็นผลใหม่.
- DATA_DICTIONARY เพิ่ม abstain_reason; WORKFLOWS ระบุ input checks/task lifecycle ตรงโค้ด.
- Mobile sidebar ปรับ focus/Escape/close-on-nav/inert; ยังไม่อ้างว่า browser accessibility ผ่าน.

## Browser: NOT_RUN

ลองรัน `apps/web/scripts/browser_check.py` จริงโดยเริ่ม backend/Vite บน loopback แล้ว. Chromium เปิดไม่สำเร็จ: socket() Operation not permitted และ process SIGABRT. Browser assertions executed = 0. `apps/web/evidence/browser-check.json` และ browser-attempt.txt เก็บเหตุผล. ไม่มี screenshots หรือ visual approval ที่สร้างขึ้นแทนการรันจริง.

Codex ตรวจต่อจาก package root:

```bash
python -m pip install -r requirements-validation.txt
python -m playwright install chromium
python apps/web/scripts/browser_check.py
```

ถ้าระบบใช้ Chromium ที่ติดตั้งเอง ตั้ง CHROMIUM_PATH ก่อนรัน. สคริปต์ครอบคลุม fixture no-write, viewer forbidden, document save, timeout, edit/approve, stale commit, lost-response retry, reload result และ mobile navigation/overflow. Test script ที่มีอยู่ไม่ได้แปลว่าแต่ละ browser case ผ่านแล้ว. DOM/state tests, typecheck และ production build ไม่แทน browser interaction/layout/focus QA.

## ขอบเขตข้อมูลและ template

- ข้อมูลใหม่18กรณีเป็น authored synthetic fixtures ที่สร้างซ้ำได้ ไม่ import runtime และไม่เป็น clinical benchmark.
- Synthea official artifact ถูกสำรวจ URL/metadata/terms แต่ NOT_DOWNLOADED/NOT_BUNDLED เพราะ artifact-specific rights ยัง UNKNOWN; raw SHA256/retrieved_at เป็น null. ไม่สรุปว่าผู้เผยแพร่ห้ามใช้ และไม่อนุมานสิทธิจาก code license.
- Template เป็น official shadcn sidebar-01 ที่ตรวจ source revision/license; copied snapshots/modified files/notice อยู่ apps/web/TEMPLATE_PROVENANCE.json. Reference sources อื่นไม่ใช่ copied assets.
- Backend singleton p-demo/e-demo/task-demo ไม่รองรับ general multi-patient/task import. หลัง task completed ใช้ DB ใหม่สำหรับ journey ใหม่; ไม่ reset หลักฐานเดิม.

## NOT_RUN / งานต่อ

Browser interaction/visual/accessibility, Windows/Python รุ่นอื่น, production framework/auth/session/SSO/TLS, external tamper-evident audit, production backup/restore, load/HA และ generic task binding ยังไม่ได้รับรอง. มี additive schema regression test ไม่ใช่ production migration rehearsal.

Live cloud/dr-train/local/specialist inference, checkpoint/runtime capability tests, token-cost benchmark, clinical/product effectiveness และ payer/financial outcome evaluation NOT_RUN. Hardware/endpoint/exact checkpoints/งบยัง UNKNOWN. Timeout/failure ใน runtime suite เป็น mock simulations; การเก็บข้อมูลและ transaction เป็น software execution จริง.

## Cross-document reconciliation

GOAL/PLAN ครอบคลุม38domainsแต่ทำ first slice เดียว. ARCHITECTURE แยก React frontend, strict stdlib backend, SQLite และ explicit mock; v1 wire shape คงเดิม. Registry/live policy fail closed. Data fixture mode ไม่เรียก mutation; API mode singleton. BACKLOG B00R–B04R ทำต่อได้โดยไม่รอ model; B05R ต้องทรัพยากรจริง. Framework migration และ browser acceptance ไม่ถูกนับว่าจบจาก audit patch/build. Root evidence เดิมเป็น historical v0.1; evidence/v0.2 และ apps/web/evidence เป็นหลักฐานของ release นี้.
