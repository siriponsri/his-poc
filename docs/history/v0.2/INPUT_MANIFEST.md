# Input manifest

วันที่ 2026-11-12. READ หมายถึงอ่านเนื้อหาในรอบงานนี้โดยผู้รวมผลหรือ agent ที่รับมอบหมาย; PARTIAL_READ ระบุช่วงที่อ่าน; NOT_READ คือได้รับแต่ไม่อ้างว่าอ่าน. Hash/แตก ZIP ไม่เท่ากับอ่านเอกสาร. ไฟล์รายแถวพร้อม SHA-256/ขนาดครบอยู่ `evidence/input-file-manifest.json`.

## Attachments และ project sources

| File | Bytes | SHA-256 | Status |
|---|---:|---|---|
| upload/01_PROMPT_GPT_WORK_TH.md | 17805 | 961d727000538830d7405d21826219b64bda22a5144db014e7dea5b9e0cb26d3 | READ |
| upload/HIS_AI_Knowledge_Library_2026-11-12.zip | 43291858 | b0a436ce186d499eff488ea4b3d95bb1c10ddd744c5a3083eacab762161c6888 | EXTRACTED_INVENTORIED |
| upload/HIS_Work_to_Codex_Handoff_2026-11-12.zip | 109177 | 855661665d5f763339f0b82830659c51f215494dd8b0b8b4b1c4e739c6d7bb3a | EXTRACTED_INVENTORIED |
| project_sources/01-deep-research-report.md | 79132 | 28c57d80db3480427045baace4b5036e1a004448ecf67a0e57e7b6ba73e3a65b | PARTIAL_READ |
| project_sources/02-HIS_AI_Knowledge_Library_2026-11-12.zip | 43291858 | b0a436ce186d499eff488ea4b3d95bb1c10ddd744c5a3083eacab762161c6888 | EXTRACTED_INVENTORIED |
| project_sources/03-HIS_Work_to_Codex_Handoff_2026-11-12.zip | 109177 | 855661665d5f763339f0b82830659c51f215494dd8b0b8b4b1c4e739c6d7bb3a | EXTRACTED_INVENTORIED |

สำเนา ZIP ใน upload และ project_sources มี hash ตรงกัน; ใช้ชุด upload แตกอ่านครั้งเดียว. รายงาน deep research ใช้เพียงบริบทและคำแนะนำ repository; citation tokens เดิมยัง unresolved.

## Content actually read

| Path | Status | Scope |
|---|---|---|
| upload/01_PROMPT_GPT_WORK_TH.md | READ | full text |
| project_sources/01-deep-research-report.md | PARTIAL_READ | lines 1–33 and 795–850; historical context only, citation tokens unresolved |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/02_PROMPT_CODEX_IMPLEMENT_TH.md | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/03_PROMPT_CODEX_REVIEW_TH.md | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/04_OWNER_BRIEF_PRE_FILLED_TH.md | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/05_RUNTIME_INVENTORY_TEMPLATE.yaml | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/06_MODEL_REGISTRY_PROPOSED.yaml | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/08_STARTER_ACCEPTANCE_TH.md | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/10_RUNTIME_MODEL_NOTES_TH.md | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/11_ARCHITECTURE_BRIEF_TH.md | READ | full text |
| inputs/handoff/HIS_Work_to_Codex_Handoff_2026-11-12/SOURCES.json | READ | full text |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/00_START_HERE/README_TH.md | READ | full |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/01_GUIDES_TH/01_HIS_FULL_SYSTEM_OVERVIEW_TH.md | READ | full text |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/01_GUIDES_TH/03_AI_ARCHITECTURE_AND_CONTROLS_TH.md | READ | full text |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/01_GUIDES_TH/04_DATA_INTEROPERABILITY_AND_LEDGER_TH.md | READ | full text |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/02_ORIGINAL_DOCUMENTS/AI04_Artificial_Intelligence_Risk_Management_Framework_AI_RMF_1_0.pdf | PARTIAL_READ | PDF pages 27–28 and 34–35; text extraction; no visual layout review |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/02_ORIGINAL_DOCUMENTS/SA05_SAFER_Guides_Patient_Identification.pdf | PARTIAL_READ | PDF pages 1–3 and 6–7; text extraction; no visual layout review |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/03_CATALOG/domain_matrix.csv | READ | parsed full rows; names/groups/acceptance read |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/03_CATALOG/source_catalog.json | PARTIAL_READ | parsed all 94 metadata records; reviewed projected ID/title/URL/limitations; this is not reading 94 original sources |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/04_TEMPLATES/ai_use_case_card_template.md | READ | full |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/04_TEMPLATES/evaluation_protocol_template.md | READ | full |
| inputs/knowledge/HIS_AI_Knowledge_Library_2026-11-12/04_TEMPLATES/interface_contract_template.md | READ | full |

## Access boundaries

- LabClear remote root tree/README/manifests ที่ commit ระบุใน REUSE_ASSESSMENT ตรวจจริง; ไม่ได้ run repository หรือดู local dirty worktree.
- PharmaCore URL/checkout UNKNOWN; scoped repository search ไม่คืนผล ไม่ได้พิสูจน์ว่า repo ไม่มี.
- ไม่มีการเข้าถึง dr-train/เครื่อง Windows, weights, endpoint หรือข้อมูลผู้ป่วยจริง.
- 94 source catalog entries เป็น metadata ที่ได้รับ ไม่อ้างอ่านหรือยืนยันต้นฉบับครบ 94 แหล่ง. PDF ส่วนใหญ่ NOT_READ; 2 ฉบับอ่านเฉพาะหน้าที่ระบุ.
- HTML/PDF คู่มือซ้ำไม่ได้อ่านใหม่หากอ่าน Markdown แล้ว. ไม่มีการนำ PDF ต้นฉบับแจกซ้ำใน starter.

## v0.2 inputs and reinspection

อ่าน WORK_NEXT_PROMPT_TH.md และ audit kit ตามลำดับที่ระบุ; exact paths/bytes/SHA-256 และขอบเขตอยู่ `evidence/v0.2/input-manifest.json`. Patch ตรวจ before/after hashes และ baseline ซ้ำในสำเนาแยก; command/evidence อยู่ `evidence/v0.2/hardening-execution.json`. หลักฐาน candidate เดิมใน audit kit ไม่แทนผลตรวจรอบนี้. โครง apps/web ใหม่ไม่มี framework เดิมนอก vanilla demo ให้ reuse. LabClear snapshot จาก v0.1 เป็น historical inspection ไม่ได้ reverify remote HEAD ในรอบ v0.2. ไม่มี local owner repository/server checkout ใหม่.

ข้อมูลเปิดที่อ่านและไฟล์ authored อยู่ `data/evidence/input_reads.json`, `data/evidence/SOURCE_REVIEW.md` และ `data/OPEN_DATA_MANIFEST.json`. Template source/license/revision/copy list อยู่ `apps/web/TEMPLATE_PROVENANCE.json`. ไม่อ้างว่าอ่าน dataset ที่ไม่ได้ดาวน์โหลด.
