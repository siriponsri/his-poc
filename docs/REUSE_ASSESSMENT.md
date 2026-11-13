# การตรวจ reuse ก่อนสร้าง starter

วันที่ตรวจ 2026-11-12; หลักฐาน `evidence/repository-inspection.json`.

ตรวจ GitHub ที่ URL ซึ่ง owner brief ระบุ: https://github.com/siriponsri/LabClear . อ่าน root tree, README, requirements.txt และ package.json; ตรึงไฟล์ทั้งสามซ้ำกับ commit `86ba619bcf481ceae214a067a37513ae9c824bca` และ blob ตรงกัน. Root AGENTS.md ตอบ 404; ไม่เท่ากับพิสูจน์ว่าไม่มีคำสั่งในโฟลเดอร์ย่อย. ไม่ได้ clone/run/test LabClear ในงานนี้ และ local branch/dirty changes บนเครื่องเจ้าของยัง UNKNOWN.

README ระบุ 4.0.0-rc3, FastAPI + Jinja + vanilla JavaScript; SQLite local/PostgreSQL hosted. requirements มี FastAPI, httpx, Jinja, pydantic-settings และ psycopg แบบ pin. Node ใช้สำหรับ optional Playwright UAT. คำสั่งที่อ่านพบคือ `uvicorn main:app --host 127.0.0.1 --port 8000` และ `python scripts/offline_check.py pytest -q`; NOT_RUN ในงานนี้. ผลคะแนนที่ README รายงานเป็นหลักฐานของ repository เดิม ไม่ใช่ผลตรวจ starter นี้.

การค้นชื่อ PharmaCore เฉพาะ user:siriponsri ไม่คืน repository; จึงยังไม่ทราบ URL/branch/commit จริง ไม่สรุปว่าโครงการไม่มีอยู่. รายงาน PharmaCore ที่แนบเป็นบริบททางผลิตภัณฑ์ ไม่ใช่ source checkout. ไม่มีการเข้าถึงเครื่อง Windows หรือ dr-train.

## คำตัดสินที่แก้กลับได้

สร้าง isolated reference starter สำหรับ shared HIS transaction contracts และ mock journey โดยไม่แก้หรือแทน repo เดิม. ใช้ Python/SQLite ให้สอดคล้องทิศทาง stack เดิม แต่ใช้ stdlib HTTP เฉพาะ local demo เพื่อลด dependency สำหรับส่งต่อ. LabClear เป็น candidate สำหรับ reuse pattern/UX/provider testing หลังตรวจ code/license/behavior ระดับโมดูล ไม่คัดลอก source จาก README หรือสรุปว่าใช้แทน shared hospital core ได้ทันที.

งานต่อ: เมื่อมี checkout จริง ให้ Codex เก็บ `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, อ่าน AGENTS ทุกระดับและ manifests ก่อนเลือก merge/module extraction. ทดสอบ scope/approval semantics ของโค้ดที่จะ reuse ด้วยชุด regression นี้; รักษางานที่ยังไม่ commit ของเจ้าของ.
