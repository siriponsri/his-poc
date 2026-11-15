# CareBalance product review and improvement roadmap

Review date:15November2026, Asia/Bangkok. Baseline source:dbdfce7. The Admin
console and README improvements in this delivery are tracked separately in the
Admin release evidence. This report proposes further work; it does not start
those features, grant new permissions or certify clinical performance.

## Main finding

The strongest next investment is better preparation quality and team
coordination. CareBalance already has a broad transactional foundation. Its
current AI trial establishes source-linked preparation and saved workflow
effects, but many outputs copy short input notes or select document titles and
dates of birth. More3D does not resolve that limitation.

The retained matrices record38localL2domains and10localL3journeys. These are
historical synthetic acceptance, not a new execution of every domain in this
review.35domains still record NOT_CONNECTED externally. D10/D11 integrations
are bounded manual-review workflows; their presence does not establish DR/CAD
predictions or general external interoperability.

The latest real application evidence records6successful model calls,5decisions
and7effects:2drafts,2newtasks and3existing-task links. Roles restrict sources;
records preparation excludes bodies and the existing nurse cannot gain labs by
selecting a profile. Those controls, immutable revisions, scope, idempotency and
the independent financial/stock rules should remain the foundation.

## Prioritized next work

Effort S/M/L is relative scope, not a delivery promise. Expected staff benefits
below are hypotheses to measure, not savings already demonstrated.

| Priority / effort | Feature | Staff journey and intended benefit | Acceptance |
| --- | --- | --- | --- |
| P0 / L | Source-aware preparation and patient timeline | Find relevant current notes, permitted results and pending work; show changes since previous review. Reduce chart hunting and correction. | Representative cases cover meaningful facts beyond titles/DOB; each fact opens its exact source/revision; relevant-source coverage improves and omissions/revocations remain visible. |
| P0 / M | Actionable team inbox | Claim work, hand it to an eligible colleague, set an operational due date and escalate overdue obligations. | Two simultaneous claims yield one owner; revocation and expected versions revalidate; escalation updates the same obligation without duplicates. |
| P0 / M | Administration and AI operations center | See users, access, sessions, queue/failures and evidence freshness together. This delivery supplies the first Admin slice. | Distinguish configured, permitted, running and qualified; show true timestamps; do not expose clinical bodies, credentials or grant platform operations by accident. |
| P1 / M | Scoped global search and quick switcher | Find HN/name, encounter, document or task beyond the first loaded page, then continue in the correct context. | Server pagination/search respects organization/facility/care scope; exact context survives navigation and closing the patient panel. |
| P1 / L | Structured intake and document preparation | Review extracted form fields against the original and create missing-information work. | Original retained; field-level provenance; duplicate identifiers conflict safely; metadata-only staff never receive clinical bodies. Deterministic required-field checks precede any new extraction adapter. |
| P1 / M–L | Closed-loop diagnostics and referral desk | Track result availability, responsible review, communication and follow-up with LabClear/DR in context. | Source corrections retain one revision chain; real external acknowledgement is distinct from local review; no automatic release/sign/grade or duplicate uncertain sends. |
| P1 / M–L | Revenue and supply exception assistants | Prepare explanations/follow-ups for missing charge evidence, unmatched receipts, expiring lots and procurement discrepancies. | Every exception cites immutable sources; existing independent approval, Decimal ledgers and quantity conservation remain authoritative; no duplicate posting/refund/movement. |
| P2 / L | Interoperability and reconciliation workbench | Dry-run scoped imports, review mappings/errors and reconcile identities before committing. | Replayed/out-of-order messages resolve consistently; ambiguous identity waits for review; external acknowledgements are real; terminology version/licensing and destination authorization are explicit. |

## Specific gaps found

**Source selection.** `assistant_collectors.py` packs whole sources into a
2,000-byte view, at most12sources. The visit trial included6of7 sources; corrected
nursing included4of12. A recent long source can displace other useful material.
Increasing model context alone does not repair the selection policy. First
design a profile-specific relevance/coverage contract and representative cases.
Do not silently change models, expose broader sources or abandon exclusion of
pristine assistant-created outputs.

**Accountability.** `Task.assignee_id` exists, but the inspected `TaskInput`
does not expose claim/reassign, due-date or priority workflow. Home reads the
oldest100open tasks, while common lists cap at200. Client-only filtering cannot
find records outside those pages. The new Admin user directory deliberately
uses server-side search and pagination; apply the same principle to clinical
work with its own permission/scoping contract.

**Status freshness.** The retained DOMAIN_COVERAGE.json D11 entry still contains
a FINAL_UI_PENDING qualifier while newer release documents record a bounded
public continuation. Neither record is silently upgraded here. Generate a
single current-release manifest referencing immutable receipts, and distinguish
historical baseline, current runtime, integration and clinical evidence.

**Operational UX.** Typed domain forms and state transitions are a substantial
base, but calendar, ward, medication, finance and supply tasks still benefit
from their own interaction patterns. Prioritize a clear next action, accountable
owner and age of work over adding more dashboard decoration.

## Immediate interface improvements

- Use human-readable account/facility choices; keep exact IDs in secondary details.
- Combine current/stale/partial preparation into one compact status area. Keep
  omitted-source counts visible without stacking notices above useful content.
- Replace ordinary-flow transport-key/hash language with a plain recovery
  action; preserve exact evidence in expandable details.
- Shorten citation lists and highlight the cited passage. Broad references to
  every included source do not explain which passage supports a particular draft.
- Keep processing nonblocking and show a real ready-for-review indication.
  Observed50–56second provider calls justify continuity, not fake progress.
- Retain the wide patient panel and default2D Operations. Keep3D optional until
  actual operational spatial data demonstrate a useful task advantage.

## Evaluation before broader automation

Measure a defined task for each role: time to find evidence, time to a reviewed
draft, navigation count, correction amount, rejection/acceptance, duplicate
follow-ups and unresolved omissions. Keep model latency separate from personnel
task time. Compare representative synthetic cases before any separately
authorized clinical or external-data evaluation. The existing six-call trial
cannot establish clinical effectiveness or saved staff minutes.

## Domain-by-domain survey

The following evidence labels are copied from the retained matrix at the base
revision. The final column is a proposal, not an implementation claim. External
status remains deliberately distinct from local workflow acceptance.

| Domain | Area | Historical local evidence | Recorded external status | Proposed next improvement |
| --- | --- | --- | --- | --- |
| D01 | ทะเบียนและตัวตนผู้ป่วย | L2 PASS | `NOT_CONNECTED` | Patient identity search and reviewed duplicate-resolution work; never automatic merging. |
| D02 | นัดหมาย คิว และความจุบริการ | L2 PASS | `NOT_CONNECTED` | A capacity-aware appointment/queue desk with ownership, operational due dates and server pagination. |
| D03 | OPD และเวชระเบียนการตรวจ | L2 PASS | `NOT_CONNECTED` | Source-aware visit preparation, chronological patient timeline and changes since the last review. |
| D04 | ห้องฉุกเฉิน | L2 PASS | `NOT_CONNECTED` | A rapid emergency-work register; operational queue priorities remain separate from medical triage. |
| D05 | ผู้ป่วยใน เตียง และการปิดการรับบริการ | L2 PASS | `NOT_CONNECTED` | A ward/bed board with explicit transfer ownership and discharge next actions. |
| D06 | งานพยาบาลและการส่งเวร | L2 PASS | `NOT_CONNECTED` | Structured handover with outstanding work and visible source omissions. |
| D07 | คำสั่งแพทย์และการจัดการคำสั่ง | L2 PASS | `NOT_CONNECTED` | Claim/reassign/due-date workflows with simultaneous-claim conflict protection. |
| D08 | เภสัชกรรมและการจ่ายยา | L2 PASS | `NOT_CONNECTED` | Medication reconciliation preparation from permitted sources; prescribing remains a separate authorized action. |
| D09 | การให้ยา ณ จุดดูแล | L2 PASS | `NOT_CONNECTED` | Due-administration work and documented exceptions; never automatic administration recording. |
| D10 | ห้องปฏิบัติการและผลวิกฤต | L2 PASS | `QUALIFIED_PUBLIC_SYNTHETIC_LABCLEAR_MANUAL_REVIEW` | Closed-loop laboratory review ownership, corrections and original-source comparison. |
| D11 | รังสี RIS และภาพทางการแพทย์ | L2 PASS | `QUALIFIED_PUBLIC_SYNTHETIC_DR_MANUAL_REVIEW_FINAL_UI_PENDING` | Image-quality/laterality readiness and unsigned review follow-up; held images stay held. |
| D12 | ห้องผ่าตัดและวิสัญญี | L2 PASS | `NOT_CONNECTED` | Surgical-case preparation with responsible owners and equipment/document checklists. |
| D13 | ICU และข้อมูลจากอุปกรณ์ | L2 PASS | `NOT_CONNECTED` | Source-linked flowsheet/trend reading with original units; no unvalidated risk prediction. |
| D14 | สูติกรรม มารดา และทารกแรกเกิด | L2 PASS | `NOT_CONNECTED` | Specialty-specific documentation templates and reviewed missing-information work. |
| D15 | กุมารเวชกรรมและการเติบโต | L2 PASS | `NOT_CONNECTED` | Age/date-sensitive record presentation derived only from verified birth metadata. |
| D16 | เวชศาสตร์ฟื้นฟูและกายภาพบำบัด | L2 PASS | `NOT_CONNECTED` | Therapy scheduling, progress and follow-up ownership. |
| D17 | ทันตกรรมและคลินิกเฉพาะทาง | L2 PASS | `NOT_CONNECTED` | Specialty documentation and order/task context rather than one generic register. |
| D18 | ธนาคารเลือดและการให้เลือด | L2 PASS | `NOT_CONNECTED` | Sample/unit/transfusion traceability and reviewed crossmatch work. |
| D19 | โภชนาการและอาหารผู้ป่วย | L2 PASS | `NOT_CONNECTED` | Reviewed diet-order preparation and explicit responsible-team handoff. |
| D20 | การส่งต่อและการติดตามผล | L2 PASS | `NOT_CONNECTED` | Referral responsibility, actual acknowledgement and unresolved-next-action tracking. |
| D21 | พอร์ทัลและการเข้าถึงของผู้ป่วย | L2 PASS | `NOT_CONNECTED` | Published-record readability, scoped request status and separately authorized notifications. |
| D22 | เวชระเบียน เอกสาร และการลงนาม | L2 PASS | `NOT_CONNECTED` | Structured document templates, cited passages and a readable revision comparison. |
| D23 | ค่าบริการ ราคา และสิทธิการรักษา | L2 PASS | `NOT_CONNECTED` | Evidence-linked missing-charge/coverage exceptions without automatic financial posting. |
| D24 | เคลม ลูกหนี้ และการกระทบยอดเงินชดเชย | L2 PASS | `NOT_CONNECTED` | Claims reconciliation dry runs and separately verified payer exchange. |
| D25 | บัญชี การเงิน การรับชำระและคืนเงิน | L2 PASS | `NOT_CONNECTED` | Unmatched payment/refund exceptions with retained independent approval. |
| D26 | ต้นทุนบริการ งบประมาณ และการวิเคราะห์ทรัพยากร | L2 PASS | `NOT_CONNECTED` | Cost explanations tied to source postings and definitions of the reported metrics. |
| D27 | จัดซื้อ สัญญา รับพัสดุ และเจ้าหนี้ | L2 PASS | `NOT_CONNECTED` | Purchase/receipt/invoice matching and reviewed supplier follow-up drafts. |
| D28 | คลังยา เวชภัณฑ์ และห่วงโซ่อุปทาน | L2 PASS | `NOT_CONNECTED` | Expiring-lot, unmatched-receipt and stock-reconciliation exceptions with quantity conservation. |
| D29 | ครุภัณฑ์และวิศวกรรมการแพทย์ | L2 PASS | `NOT_CONNECTED` | Asset maintenance work with accountable owners and operational due dates. |
| D30 | บุคลากร ตารางเวร และสมรรถนะ | L2 PASS | `NOT_CONNECTED` | Roster eligibility tied to current memberships and verified staff references. |
| D31 | CSSD ซักฟอก อาคาร และบริการสนับสนุน | L2 PASS | `NOT_CONNECTED` | Service-request ownership and operational escalation rules. |
| D32 | คุณภาพ ความเสี่ยง และการควบคุมการติดเชื้อ | L2 PASS | `NOT_CONNECTED` | Incident review and traceable corrective-action follow-up. |
| D33 | รายงานสาธารณสุขและข้อมูลระดับเครือข่าย | L2 PASS | `NOT_CONNECTED` | Schema-validated public-health reporting and source reconciliation before external submission. |
| D34 | ตัวตนผู้ใช้งาน สิทธิ และการตรวจสอบการเข้าถึง | L2 PASS | `NOT_CONNECTED` | Dedicated administration, exact account identity, session control and truthful service configuration. |
| D35 | การเชื่อมต่อระบบ คำศัพท์ และคุณภาพการแลกเปลี่ยน | L2 PASS | `NOT_CONNECTED` | Versioned adapter mapping, dry-run imports, replay/out-of-order reconciliation and real acknowledgements. |
| D36 | คลังวิเคราะห์ ข้อมูลวิจัย และการใช้ข้อมูลรอง | L2 PASS | `NOT_CONNECTED` | Metric definitions, data freshness and measured staff-task outcomes. |
| D37 | AI และระบบช่วยตัดสินใจ | L2 PASS | `VERIFIED_NAMED_SYNTHETIC_DOCUMENT_ROUTE` | Relevant-source selection and useful synthesis beyond titles/DOB, with exact citations and review. |
| D38 | การเดินระบบ ความต่อเนื่อง และการกู้คืน | L2 PASS | `NOT_CONNECTED` | One current-release manifest and bounded operational recovery with actual restore evidence. |

## Inspected sources and primary references

Source: [domain coverage](../DOMAIN_COVERAGE.json),
[journey coverage](../JOURNEY_COVERAGE.json),
[domain requirements](../spec/DOMAIN_IMPLEMENTATION_MATRIX.md),
[actual AI trial](../evidence/ai-driven-root-20261114/application-acceptance.json),
[collector](../backend/app/assistant_collectors.py),
[profiles](../backend/app/assistant_profiles.py),
[task model](../backend/app/models.py), [task inputs/core](../backend/app/core.py),
[Home queue](../apps/web/src/components/home-workspace.tsx),
[preparation UI](../apps/web/src/components/care-workspace.tsx) and
[current release](RELEASE_AI_WORKSPACE.md).

Current primary references inform the proposals; they are not evidence that
CareBalance already implements those products' capabilities:

- [Medplum:Tasks and work queues](https://www.medplum.com/docs/careplans/tasks):
  ownership, role eligibility, stages and due dates inform the proposed inbox.
- [Medplum:Automating care workflows](https://www.medplum.com/docs/careplans/automating-workflows):
  event-specific work and repeat-delivery reconciliation inform coordination.
- [Oracle Health EHR:Ask Oracle introduction](https://docs.oracle.com/en/industries/health/oracle-health-ehr/ehrug/introduction3.html):
  separate chart, message and documentation workflows inform role-focused agents.
- [Microsoft:Dragon Copilot introduction](https://learn.microsoft.com/en-us/industry/healthcare/dragon-copilot/about/):
  contextual documentation drafts with clinician review inform the preparation
  pattern; ambient capture/transcription is not a current CareBalance claim.

Audit method: read-only repository/evidence inspection and primary-source
research. This audit made no server, database, model or external-connector call
and did not rerun the38-domain clinical baseline.
