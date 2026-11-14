# CareBalance interface system

The owner selected this combination on 14 November 2026:

- Clinical Workspace: main work queue and login composition.
- Patient Record: stable patient/encounter context, document list and readable detail.
- Operations Desk: the original loop mark and CareBalance wordmark, shared throughout.

This supersedes the 13 November triadic layout. The palette anchors remain blue
#1C4286, burgundy #861C42 and green #42861C. Neutral surfaces carry the interface;
color identifies an action or meaningful finding. English primary headings and
navigation sit alongside Thai clinical content and explanations. Self-hosted Latin
and Thai typography replaces the earlier IBM Plex treatment, with license notices
retained alongside the fonts.

## Composition and data

The main workspace keeps a scoped task table beside details for the selected
item. Patient work retains identity and encounter while documents, visits and
related work change. Navigation remains permission-filtered, including all 38
existing domain destinations, and becomes a focus-contained drawer on mobile.
Login exposes only the actual local account flow and public neutral illustration.

All rows, counts, versions and findings come from authorized APIs. The design
proposal fixtures do not populate the app. Missing metadata is not invented, and
loaded collection sizes do not claim global totals. Important status is readable
in words; colored leading card stripes and pill stacks are not part of this system.

## Patient reading journey

Patient names in the queue open a separate wide, read-only dialog, retaining the
queue behind it. On the actual1536px public desktop viewport the panel is1120px
wide and source area790.4px, replacing the330px preview as the main reading space.
At390px mobile width, a native document selector leaves356.8px for source reading.
These are observed dimensions, not a user study or a breakpoint guarantee.

Document selection remains inside the panel. Visits expand into a list; Open visit
continues in the existing visit workspace, where encounter selection belongs.
Open document and Open review carry exact document/task/patient/encounter context.
The panel has no editing, AI execution or approval actions. Escape/Close restore
trigger focus and queue position; route/Login/logout navigation resets the viewport.
Loading, empty and denied/error states are distinct; retry uses close and reopen.

See [User journey](docs/USER_JOURNEY_TH.md) and
[release evidence and limits](docs/RELEASE_PATIENT_PANEL.md). The separate CareBalance
DR derivative and LabClear theme integration remain active future implementation.

## Workflow invariants

Task links retain exact task/patient/encounter context. Patient changes clear old
drafts/results through the existing boundaries. Proposals must match the current
patient and encounter; unknown metadata fails closed. Authorized history without
matching context remains read-only. Edits, approval and commit bind the selected
proposal version, hash, source evidence and stable operation key.

D22 retains immutable revision reading/editing/attestation. D37 preserves actual
provider labeling, source quotes, human editing, approval and atomic commit.
Network ambiguity and replay keep the original operation key; provider failure
does not switch to mock or cloud. Source containment does not establish clinical
accuracy. Loading, empty, error, denied, pending, unsaved and recorded states retain
their existing actions and keyboard behavior.

## Evidence and references

See [selected design contract](docs/design/CLINICAL_WORKSPACE.md) for research,
provenance and release boundaries. Historical implementation evidence remains in
[the prior design record](docs/design/TRIADIC_REDESIGN.md); it is not proof of this
iteration. Current release evidence identifies the candidate, checks and deployed
image separately from the original 38-domain local acceptance.
