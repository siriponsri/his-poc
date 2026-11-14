# J01–J10 local L3 coverage

The additional AI preparation release is tracked separately: runtime9afd/schema0005
is deployed; four direct synthetic profile fixtures passed source fidelity, while
foreground worker and actual application preparation/review/watch acceptance
remain pending. These checks do not replace or expand the historical38-domain/
10-journey baseline. [Deployment](evidence/ai-driven-root-20261114/deployment-readback.json)
and [model qualification](evidence/ai-driven-root-20261114/live-source-fidelity.json).

All ten local synthetic journeys have executed PostgreSQL and rendered-browser evidence. Successful scenarios were composed from retained runs; original failed attempts were not upgraded or erased. Exact API and browser record IDs are separate in [JOURNEY_COVERAGE.json](JOURNEY_COVERAGE.json).

| Journey | API + PostgreSQL | Real browser | Local level | Browser source |
|---|---|---|---|---|
| J01 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J02 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J03 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J04 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J05 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J06 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J07 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J08 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-accepted/browser-journeys.json |
| J09 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journeys-J09-J10-accepted/browser-journeys.json |
| J10 | PASS | PASS | L3 | apps/web/evidence/fullsystem/windows-journey-J10-accepted/browser-journeys.json |

Supporting gates: browser recovery PASS9; final-image smoke PASS11; read-only verification of the actual UI restore PASS109 tables/1 file/8 exact browser records. Baseline D37 is MOCK. A subsequent J01 document-review extension uses real pinned Typhoon on dr-train: browser PASS7 + read-only PASS2, with separate IDs/evidence in JOURNEY_COVERAGE.json. Other live interfaces, clinical validation and production deployment remain separate.

## Additional protected public manual-review subsets

The14 November LabClear subset associated with J02 passed released source6 to
reviewed7, explicit confirmation, reload/read-only reopen and persisted readback;
original source6/v10 remains unchanged and the HIS review task stays open.
The public DR subset associated with J08 passed explicit source consent, fixed
patient/visit/eye context, original640x480 image preview, manual quality and
patient/eye confirmation, unsigned draft save/full reload and an explicit
unsigned review check. No clinical signing or model call occurred. The final
DR human-label bundle refresh/post-refresh preservation pass; label-only public
browser smoke is NOT_RUN after the physical Escape stop. [Public receipts](evidence/integrations/public-dr-20261114/receipts.json)
and [integration checkpoint](docs/integrations/VALIDATION_CHECKPOINT_20261114.md).

These are bounded synthetic extensions, not a rerun of the complete local J02,
J08 or all10 L3 journeys. The original L3 records above retain their date/scope;
real-patient transfer, DR model performance and clinical effectiveness remain
unverified. Ten owner-renamed MMRDR images remain held for laterality.

## Additional public document/AI subset

The protected dr-train deployment passed the document→real-AI→human editv2→approve→commit→reload subset associated with J01. This is not a complete repeat of registration or all10 journeys. Original local L3 evidence is retained. See evidence/triadic-release/public-final/browser-acceptance.json and evidence/deployment-20261113/public-workflow-readback.json.
