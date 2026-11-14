# Source-bound assistant adapter: offline checkpoint

2026-11-14. Root candidate adds `assistant_provider.py`, `assistant_schema.py`
and their focused transport/schema tests. Existing D37 provider files are unchanged.

- PASS: 52 tests (`test_assistant_provider.py` plus existing
  `test_document_provider_unit.py`), 5.53s. Network uses explicit HTTP transport
  doubles; these tests make no real model calls.
- PASS: Ruff checks on the three new files.
- Independent architecture review found three blockers: cross-citation draft
  numbers/unchecked titles, ungrounded gap kind/title, malformed capability
  metadata. Root fixed all three and added regression cases. Draft effects must
  cover the draft's citations. Workflow gaps require a supporting typed field;
  displayed gap titles are fixed server templates.
- Facts remain exact typed values or exact source quotes. Draft semantic/clinical
  correctness still requires review; numeric validation is not clinical validation.
- Default configuration disables inference. Configured profiles remain unqualified
  until separately measured live synthetic qualification. No fallback or automatic
  retry exists. Unknown monetary cost is null.

NOT_RUN at this checkpoint: integrated PostgreSQL worker/provider tests, four
live staff profiles, authenticated public workflow, deployment of the new feature.
The separately recorded neutral infrastructure probe is not profile qualification.
