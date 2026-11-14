# AI-driven Care Workspace: v1 implementation contract

Status: ACTIVE IMPLEMENTATION, not yet deployed or live-profile qualified.
Owner direction: reduce personnel work across clinical/nursing, medical
records/administration and laboratory teams; use dr-train first; add a useful
optional genuine 3D hospital/agent-office operations view.

## Product behavior

The primary workspace prepares eligible visits together, presents source-linked
facts and editable drafts, and lets a person use a draft or create/link follow-up
work in one explicit action. A persistent, bounded watch keeps selected visits
prepared when their eligible source data change. Page loads, source reads and
3D camera movement never dispatch inference. Existing domain workflows remain.

Four profiles share one protocol:

| Profile | Existing preparation permissions | Sources and initial effects |
| --- | --- | --- |
| visit_preparation | D37.write, D03.read, D22.read, documents.content | Permitted notes, released labs only with D10.read, permitted tasks; new D22 draft and create/link D37 document_review |
| nursing_handover | D06.read/write, D03.read, D22.read, documents.content | Permitted notes/D06/tasks; D22 handover draft and D06 follow-up. Current nurse has NO D10 access |
| records_readiness | D01.write, D03.read, D22.read | Patient/visit fields and document title/status/version/revision/hash only; D01/D22 metadata-review tasks. NO note bodies, hidden revision authors, clinical drafts or guessed demographics |
| laboratory_handoff | D10.read/write, D07.read, D03.read | Released/corrected lab values/units/ranges/recorded flags and scoped review tasks; create/link D10 labclear_review/follow-up. No new orders, signatures, release/correction or invented thresholds |

Persisted effective permissions and current patient/facility/organization scope
are authoritative. No role grants are added. Nurse production acceptance uses
already assigned patient-001; new-six access is not inferred. Registration is
the existing login for the medical_records role alias. A broader user's records
profile remains metadata-only. Clinical approval/attestation stays separate.

## Frozen service boundary

Provider-owned `assistant_schema.py` and `assistant_provider.py` expose:

```text
prepare_assistant(profile, locale, inference_view) -> {
  artifact: {facts[], work_gaps[], drafts[], suggested_effects[], requires_review:true},
  provenance: object, usage: object|null, measured_cost:null, elapsed_ms:number
}
validate_assistant_artifact(profile, artifact, inference_view) -> validated artifact
assistant_provider_config() -> declared/configured status; no generation
```

Full authoritative manifests stay server-side. Compact inference_view is:

```json
{
  "profile": "laboratory_handoff",
  "locale": "th",
  "sources": [
    {"ref":"s1","kind":"patient","fields":{"display_name":"นามสมมุติ","sex":"male","age":"58"}},
    {"ref":"s2","kind":"lab","fields":{"analyte":"Fasting plasma glucose","result_value":"152","unit":"mg/dL","reference_range":"70-99","result":"Fasting plasma glucose: 152 mg/dL (70-99)","status":"released","critical":false}}
  ],
  "coverage":{"eligible_sources":2,"included_sources":2,"omitted_sources":0,"unavailable_domains":[]},
  "effect_candidates":[{"action_id":"a1","kind":"link_lab_review_task","source_refs":["s2"]}]
}
```

Facts use `{source_ref,field,quote,display}`. Typed facts' display is constructed
from the exact permitted field; document facts cite an exact included quote.
Provider validation may add display from the verified source. Gaps use
`{kind,source_ref,field,quote,title}` with evidence. Drafts use
`{id,title,text,source_refs[]}`. Suggested effects select server-owned candidate
`action_id`, matching `kind`, `source_refs[]`, optional `draft_id`; no arbitrary
patient/endpoint/model/SQL/tool/domain/URL. Metadata tasks use server templates.
No records-profile draft or document-body inference input is permitted.

Use separately versioned prompts and strict JSON Schema. Preserve exact quoted
text and typed numerical/unit strings. Narrative drafting still requires human
review; quote validation is not clinical certification. No diagnosis, dose,
medical triage, referral decision or clinical signing is an assistant effect.

## API and DTOs

```text
GET  /api/v2/assistant/config
GET  /api/v2/assistant/worklist
POST /api/v2/assistant/batches
POST /api/v2/assistant/runs
GET  /api/v2/assistant/runs/{id}
POST /api/v2/assistant/watches
GET  /api/v2/assistant/watches
POST /api/v2/assistant/watches/{id}/pause
POST /api/v2/assistant/runs/{id}/apply
GET  /api/v2/assistant/operations-map
```

Config: `{enabled, profiles:[{id,label,available,allowed_effects}], default_profile,
provider:{configured,qualified,route,model_digest}, limits}`. No page-read inference.
Single run request: `{profile,patient_id,encounter_id,locale,expected_source_digest?}`.
Batch: `{profile,selection:"my_eligible_work",maximum_contexts:6,keep_prepared:true,
watch_minutes:30,locale:"th"}`. POSTs require CSRF and Idempotency-Key.

Worklist: `{items:[RunDTO],eligible_contexts:[{patient_id,encounter_id,patient_label,
patient_reference,profile}],watches:[],counts:{},scope:"authorized_work"}`.
RunDTO: `{id,profile,patient_id,encounter_id,patient_label,execution_state,review_state,
source_digest,source_freshness,coverage,sources:[{ref,kind,label,fields,quote?,url?}],
revision:{id,version,content_hash,facts,work_gaps,drafts,suggested_effects}|null,
effects:[],provider,usage,measured_cost,created_at,completed_at,error|null}`.
Source responses revalidate content permission. No less-privileged user receives
a clinical artifact created under broader source permissions.

Apply: `{expected_revision_id,expected_version,expected_content_hash,
expected_source_digest,selected_action_ids:[],edited_draft_text:null}`. One
transaction may append a human-edited revision, explicit acceptance decision,
selected normal draft/task effects, audit, effect receipt and idempotent response.
Unique effect identity prevents duplicate documents/tasks even under another key.
Reuse appropriate existing OPEN reviews. No inference during apply.

Operations map: `{scope:"authorized_work",refreshed_at,zones:[{id,label,domains:[],
available,open_task_count:null|number,awaiting_review_count:null|number}],agents:
[{profile,label,run_id:null|string,execution_state,review_state,patient_label?}]}`.
Absent permission is unavailable/null, never a fabricated zero. Rooms open the
same scoped worklist; run markers open actual artifacts. Idle remains idle.

## Persistence, watches and admission

Five additive tables: AssistantRun, AssistantRevision, AssistantDecision,
AssistantEffect, AssistantWatch. Immutable revisions/decisions/effects; existing
single-document Proposal/D37 contract is preserved.

Execution: queued, waiting_for_capacity, running, succeeded, failed, timeout,
invalid_output, abstained, stale_context, interrupted. Review: unavailable,
pending, accepted, rejected, superseded, stale. Effects: proposed/applied/blocked.

Watch opt-in binds actor/session/profile/patient/encounter and expiry. Defaults:
scan30s, duration30min, minimum run interval60s, maximum6 active watches and6
queued contexts per actor, maximum3 automatic runs/watch, one active HIS inference.
Use PostgreSQL leases/SKIP LOCKED and stable actor/profile/context/source digests.
Revalidate actor/session/care/source before and after inference; release DB
transaction before HTTP generation. Share admission across legacy InferenceRun
and AssistantRun, not separate unchecked provider slots. Retain failures and
timeout hold/grace; no automatic same-digest retry or new-key bypass.

Exclude ALL pristine assistant-created drafts/tasks across profiles from model
input and trigger digests, using effect-origin revision/hash/version/state.
Human edits/attestation or task-state changes become eligible. Exclude scan/run/
review timestamps/state and generated-output counts from trigger digest. Display
those actual counts separately. Detect omitted-but-eligible changes; disclose
coverage/selection; do not query inaccessible domains to count hidden records.

## Runtime and 3D

Prefer the verified existing Typhoon artifact on a dedicated private GPU0-only
service; shared11434 and research GPU1 remain unchanged. Exact weight4a1f3668…
matches pinned upstream bytes; original acquisition revision remains unknown.
GPU visibility is not exclusive capacity. Fresh resource admission and actual
bounded4096-context qualification are required; legacy8192 redirect requires
separate compatibility qualification. No new model/download/cloud fallback.

Use direct Three.js0.187.0 plus matching development types, lazy loaded only for
the optional 3D view. Authored illustrative hospital layout, real orbit/picking,
actual job states/counts, equivalent DOM/list controls, WebGL fallback, reduced
motion and resource cleanup. No pretend staff locations or agent activity.

## Qualification and ownership

Backend owns models/migration/collectors/watch/queue/shared admission/effects/API
and meaningful PostgreSQL regressions. Root owns provider prompts/schema/verified
transport plus source/role validation tests. Frontend owns workspace/3D/client/
navigation/dependencies and component/browser checks. Frozen DTO changes require
coordination, never silent parallel alternatives.

Migration0005 needs a separately qualified rollback/readiness image: current8b
hardcodes0004. No normal production downgrade/restore. Verify all old sources,
results/roles/permissions, DR/LabClear and held MMRDR preservation.

Acceptance: actual qualified dr-train inference for all four profiles/three
staff groups; source-linked artifact → permitted draft/task once → reload;
scope/revocation/stale-source/invalid-quote/wrong-value/timeout/dedup guards;
unchanged watch zero calls, changed source one queued run, no cross-profile
feedback; 2D/3D reflect the same actual states; protected URL journeys. Record
latency, source opens, human edits and actual applied effects. No saved-time
percentage or clinical-effectiveness claim is established.

Research: [Oracle workflow separation](https://docs.oracle.com/en/industries/health/oracle-health-ehr/ehrug/introduction3.html),
[Dragon Copilot](https://learn.microsoft.com/en-us/industry/healthcare/dragon-copilot/about/),
[Medplum tasks](https://www.medplum.com/docs/careplans/tasks),
[workflow automation](https://www.medplum.com/docs/careplans/automating-workflows),
[primary workload trial](https://pmc.ncbi.nlm.nih.gov/articles/PMC12768499/),
[Ollama0.12.6 configuration](https://raw.githubusercontent.com/ollama/ollama/v0.12.6/envconfig/config.go),
[Three.jsr187](https://github.com/mrdoob/three.js/releases/tag/r187).
