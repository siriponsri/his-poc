# Domain coverage — 38 local L2 workflows

The additional AI preparation release is tracked separately: runtime9afd/schema0005
is deployed; foreground worker and six real application calls passed bounded
preparation/review/watch acceptance across four profiles. The public browser
covered one visit; other roles used normal production APIs. These checks do not
replace or expand the historical38-domain/
10-journey baseline. [Deployment](evidence/ai-driven-root-20261114/deployment-readback.json)
and [model qualification](evidence/ai-driven-root-20261114/live-source-fidelity.json).

All 38 domains passed local synthetic PostgreSQL and rendered UI acceptance. L2 describes this prototype scope; named external verification is reported separately; clinical/production effectiveness remains unverified. Per-domain scenarios, source reports and hashes are retained in [DOMAIN_COVERAGE.json](DOMAIN_COVERAGE.json).

Additional14 November public subsets are recorded separately: D10 LabClear
manual review passes explicit import/confirm/reload without changing the released
HIS source; D11 DR manual quality/context confirmation and unsigned draft
save/reload pass on authored synthetic images. Final DR human-label static
refresh/post-refresh preservation pass; label-only public browser smoke remains
NOT_RUN after the physical Escape stop. [Public receipts](evidence/integrations/public-dr-20261114/receipts.json). These
subsets do not promote the local L2 baseline or establish DR inference/clinical
effectiveness. [Current integration checkpoint](docs/integrations/VALIDATION_CHECKPOINT_20261114.md).

| Domain | Name | Implementation | Verified | External |
|---|---|---|---|---|
| D01 | ทะเบียนและตัวตนผู้ป่วย | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D02 | นัดหมาย คิว และความจุบริการ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D03 | OPD และเวชระเบียนการตรวจ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D04 | ห้องฉุกเฉิน | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D05 | ผู้ป่วยใน เตียง และการปิดการรับบริการ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D06 | งานพยาบาลและการส่งเวร | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D07 | คำสั่งแพทย์และการจัดการคำสั่ง | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D08 | เภสัชกรรมและการจ่ายยา | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D09 | การให้ยา ณ จุดดูแล | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D10 | ห้องปฏิบัติการและผลวิกฤต | Local PostgreSQL workflow | L2 PASS | Public synthetic LabClear manual-review subset PASS |
| D11 | รังสี RIS และภาพทางการแพทย์ | Local PostgreSQL workflow | L2 PASS | Public synthetic DR manual-review subset PASS; final UI smoke pending |
| D12 | ห้องผ่าตัดและวิสัญญี | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D13 | ICU และข้อมูลจากอุปกรณ์ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D14 | สูติกรรม มารดา และทารกแรกเกิด | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D15 | กุมารเวชกรรมและการเติบโต | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D16 | เวชศาสตร์ฟื้นฟูและกายภาพบำบัด | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D17 | ทันตกรรมและคลินิกเฉพาะทาง | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D18 | ธนาคารเลือดและการให้เลือด | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D19 | โภชนาการและอาหารผู้ป่วย | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D20 | การส่งต่อและการติดตามผล | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D21 | พอร์ทัลและการเข้าถึงของผู้ป่วย | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D22 | เวชระเบียน เอกสาร และการลงนาม | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D23 | ค่าบริการ ราคา และสิทธิการรักษา | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D24 | เคลม ลูกหนี้ และการกระทบยอดเงินชดเชย | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D25 | บัญชี การเงิน การรับชำระและคืนเงิน | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D26 | ต้นทุนบริการ งบประมาณ และการวิเคราะห์ทรัพยากร | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D27 | จัดซื้อ สัญญา รับพัสดุ และเจ้าหนี้ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D28 | คลังยา เวชภัณฑ์ และห่วงโซ่อุปทาน | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D29 | ครุภัณฑ์และวิศวกรรมการแพทย์ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D30 | บุคลากร ตารางเวร และสมรรถนะ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D31 | CSSD ซักฟอก อาคาร และบริการสนับสนุน | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D32 | คุณภาพ ความเสี่ยง และการควบคุมการติดเชื้อ | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D33 | รายงานสาธารณสุขและข้อมูลระดับเครือข่าย | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D34 | ตัวตนผู้ใช้งาน สิทธิ และการตรวจสอบการเข้าถึง | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D35 | การเชื่อมต่อระบบ คำศัพท์ และคุณภาพการแลกเปลี่ยน | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D36 | คลังวิเคราะห์ ข้อมูลวิจัย และการใช้ข้อมูลรอง | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |
| D37 | AI และระบบช่วยตัดสินใจ | Local PostgreSQL workflow + opt-in live document review | L2 PASS | Named synthetic document route PASS |
| D38 | การเดินระบบ ความต่อเนื่อง และการกู้คืน | Local PostgreSQL workflow | L2 PASS | NOT_CONNECTED |

D37 defaults to explicit DEMO mock. An opt-in Typhoon/Ollama dr-train route passed three authored Thai document cases, seven live-browser assertions and two read-only assertions. This named scope does not promote DR/CAD or the whole domain to clinical/L4 acceptance. See docs/DR_TRAIN_AI.md. UI conflict/scope/audit/restart and real backup/isolated restore are supported by the recovery and read-only restore evidence. Initial failures remain in the evidence history.

## Additional protected deployment check

D22 and D37 have a separately executed synthetic public document/real-AI/edit/approval/commit/reload flow on his.ai-cie.com. Original38-domain local L2 levels and baseline evidence remain unchanged. Exact receipt: evidence/triadic-release/public-final/browser-acceptance.json and evidence/deployment-20261113/public-workflow-readback.json. No other external adapter or clinical claim is promoted by this check.
