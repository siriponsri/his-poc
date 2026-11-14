# LabClear review UI candidate

This is an undeployed frontend source/component checkpoint. The parent integrator
owns browser acceptance, backend integration validation, publication and deployment.

The D10 released/corrected result action opens a separate wide, keyboard-contained
review dialog. It shows the exact source cells, scoped patient/visit reference
names where available, an explicit separate review task, source transfer and
human same-person/value confirmation. Technical references are collapsed.

Pending mutation keys and payloads remain unchanged. An unknown result prevents
dismissal and warns before leaving. Opening an existing review first checks the
authorized recovery endpoint; restored commands are displayed and are never
automatically submitted. Active leases require an explicit status check. The
another-tab pending fence reloads authorized bindings and offers recovery.
Unknown reads can be repeated without treating them as new source mutations.

Latest source is frozen in `historical-read/source-before.json` and
`historical-read/source-after.json`:53 source/test/public inputs, zero drift across checks.
`checks.json` records exact command results and owned-file hashes. Earlier files
outside `historical-read/`, including the earlier `final/` candidate, retain
their preceding implementation-phase evidence.

The historical-read follow-up fixes the reviewed write-scope regression:
confirmed bindings use the authorized read endpoint directly. Existing drafts
whose scoped task is completed or whose visit is closed are readable without
recovery, with disabled fields and no confirmation controls. These drafts are
labelled saved reviews, never confirmed reviews. Active unresolved mutations
still use the explicit original-command recovery path.

- PASS:25 unit tests.
- PASS:115 mounted component tests, including24 LabClear workflow/accessibility
  cases and the existing38 mounted domain-route checks.
- PASS:3 legacy audit probes executed without reproducing their targeted defects.
  This is probe execution, not full application acceptance.
- PASS:typecheck, production build and emitted LabClear CSS/script inspection.
- NOT_RUN:actual browser rendering/responsiveness, PostgreSQL/receiver/public
  end-to-end acceptance, OCR/AI, deployment, commit or push.

The previously reported memory/test hang did not reproduce. No cause is assigned
to it, and no unrelated process was terminated. Full component checks used two
workers and a20-second per-test timeout.
