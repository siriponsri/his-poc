# J01–J10 local L3 coverage

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

## Additional public document/AI subset

The protected dr-train deployment passed the document→real-AI→human editv2→approve→commit→reload subset associated with J01. This is not a complete repeat of registration or all10 journeys. Original local L3 evidence is retained. See evidence/triadic-release/public-final/browser-acceptance.json and evidence/deployment-20261113/public-workflow-readback.json.
