# Contracts v1 — isolated legacy regression

Historical v0.2 implementation only. The current default app mounts v2 and returns404 for v1; old public tokens do not authenticate it. The runtime/current wording below describes the isolated legacy server, not the current application. See ../v2/README.md.

JSON Schema Draft 2020-12. These files distinguish `IMPLEMENTED_API_SHAPE` from design targets in `x-implementation-status`. HTTP runtime performs its own checks; it does not load all these JSON Schema files. Contract test coverage and schema validation results are reported separately.

The current API uses `patient`, `encounter`, `proposal_id` fields; AI adapter design envelopes use explicit `*_id` fields. Conversion belongs inside the backend adapter boundary and is not yet implemented. Do not send an ai_request directly to `/api/v1/proposals`.

The current proposal/action/snapshot and document content in context responses are serialized JSON strings. This is deliberate documentation of the demo shape, not a claim that the target API already returns expanded objects. API_IMPLEMENTATION.md is authoritative for actual routes; additive field changes require synchronized schemas/tests.

Approval binds version + canonical action SHA-256. Canonicalization implemented by Python json.dumps ensure_ascii=False, sort_keys=True, separators=(',', ':') then UTF-8. This is a project-specific rule, not an RFC 8785 conformance claim. Proposal expires after 900 seconds from creation, including review time. Edit does not renew expiry.

Specialist contracts are design-only. DR grading labels 0–4 are a proposed schema range, not an agreement with an existing model. Confirm label mapping, eye, image count, field of view, quality, masking/full image paths, model artifact and score meaning before connecting. CAD endpoint target/horizon/features/units/population must be agreed before adapter implementation. Neither output authorizes diagnosis/treatment.

Errors in runtime include FORBIDDEN_SCOPE (403), NOT_FOUND (404), invalid request (400), STALE_PROPOSAL / EXPIRED_PROPOSAL / STALE_CONTEXT / INVALID_STATE / NOT_APPROVED / IDEMPOTENCY_CONFLICT (409). Provider failures are persisted run outcomes; no proposal is created and no cloud/mock fallback occurs. HTTP success carrying `outcome=failed` is a completed workflow request with a failed inference outcome, not inference success.

Design event envelope is not a live event bus. External side effects require transactional outbox and acknowledgement/reconciliation contract before activation. Internal audit uses Unix UTC seconds; design integration envelope uses RFC3339 UTC. These types are explicitly different.

Version rules: backward-incompatible fields or semantics create v2; optional fields can be additive only if clients/tests tolerate them. Pin schema/prompt/model/config versions in evidence records before live use.

Optional verification command: `python contracts/check_contracts.py` from package root. It requires jsonschema 4.26.0 in the verification environment; runtime remains stdlib-only. Current checks validate 23 definitions, 2 examples, 176 request/schema parity cases, 27 fresh local HTTP responses and 27 frozen HTTP captures in fixtures/workflow.json. Request validation happens before dispatch using a stdlib validator; the schemas are not loaded on each request. Parity cases are finite, not formal equivalence or exhaustive fuzzing. Specialist contracts remain design-only. Use `--write-fixtures` only for intentional fixture regeneration and review the diff.

Review requests allow edits only for edit; approve/reject omit that property. Positive integral JSON numbers such as 1.0 normalize to Python int before service invocation, while Boolean versions are rejected. Task scope remains p-demo/e-demo/task-demo; a completed task cannot start a second journey. The new nullable run abstain_reason field is additive and retained after reload.
