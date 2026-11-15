# In-app user-guide content

The guide explains the current synthetic CareBalance workflows in Thai, with
English topic headings and actual control names. It is task guidance, not a
clinical protocol, an expansion of permissions or a claim that every domain is
connected to an external system.

Source baseline: **74795e2dc8a01f7fcc7f90132aa0acad0874e855**, inspected on
15 November 2026, Asia/Bangkok. The new guide UI, media, navigation and deployment
are integrated separately by the parent task. This content task does not invoke
the application, a model, an external connector or a production mutation.

## Content contract

The authored source is
[user-guide-content.ts](../apps/web/src/data/user-guide-content.ts). It exports:

- **GuideStep**: title, paragraphs, optional screenshot ID and optional note.
- **GuideChapter**: ID, title, summary, role tags, prerequisites, steps,
  completion checks, troubleshooting pairs and related domain IDs.
- **GuideDomain**: ID, name, purpose, role tags, four task steps, completion
  check and limits.
- **GUIDE_CHAPTERS**: 16 chapters with 101 ordered steps.
- **GUIDE_DOMAINS**: 38 unique references, D01 through D38, with 152 steps.

Every chapter has prerequisites, a result to verify and recoverable failure
paths. The domain references identify the current forms and transition labels
without claiming a new execution of all domain acceptance suites.

Role tags use canonical default role IDs. They help readers filter topics;
they do not check or grant permissions. The content's ROLE_DOMAINS records the
broad default writer-role mapping from backend/app/auth.py. Current persisted
permissions, organization/facility scope, care assignment, competency checks
and action-specific authorization remain authoritative. An auditor may read
applicable sections without gaining the write actions described for staff.

## Chapter map

| ID | Reader's task | Related domains |
| --- | --- | --- |
| getting-started | Pass Access, sign in, check identity and sign out | D34 |
| workspace | Choose prepared work, queue or optional Operations | D03, D07, D22, D37 |
| patient-record | Read the wide record and continue in the same context | D01, D03, D22 |
| registration-visits | Register, book, check in and manage visits/episodes | D01–D05 |
| documents | Create, revise, review and attest source documents | D22 |
| document-review | Compare a one-document completeness proposal and commit its reviewed version | D22, D37 |
| ai-preparation | Prepare role-scoped work, inspect omissions, apply selected effects and manage watches | D01, D03, D06, D10, D22, D37 |
| team-tasks | Track tasks and send/acknowledge nursing handover | D06, D07 |
| orders-medication | Sign orders, dispense and record administration separately | D07–D09 |
| laboratory | Release HIS values, transfer and confirm a separate LabClear review | D07, D10 |
| dr-screening | Inspect image context/eyes, confirm transfer and open an authorized destination | D11 |
| finance | Review charges, simulated claims, receipts and independent refund requests | D23–D26 |
| supply-operations | Procurement, stock, equipment, staff, support services and CAPA | D27–D32 |
| portal-reporting | Subject-scoped portal, reports, local exchange and secondary datasets | D21, D33, D35, D36 |
| administration | Users, memberships, care assignments, sessions and security | D34 |
| recovery | Same-request recovery, conflicts, permission changes and operator boundaries | D34, D37, D38 |

## Inspected facts and sources

| Content | Inspected implementation/reference |
| --- | --- |
| Scope and retained evidence | AGENTS.md, START_HERE.md, GOAL.md, PLAN.md, BACKLOG.md, CODEX_HANDOFF.md, VALIDATION_REPORT.md, DOMAIN_COVERAGE.md, JOURNEY_COVERAGE.md |
| Canonical domain names and scope | spec/DOMAIN_IMPLEMENTATION_MATRIX.json, apps/web/src/data/full-domains.json; the matrix is a specification and its old planning status is not used as current runtime proof |
| Actual domain forms and actions | apps/web/src/data/resource-catalog.json, backend/app/domains/clinical_catalog.json, backend/app/domains/erp_catalog.json, plus clinical.py and erp.py transaction guards |
| Patients, encounters, tasks, orders and documents | apps/web/src/components/core-workspaces.tsx, forms.tsx, workspace.tsx, App.tsx |
| Queue and wide patient panel | home-workspace.tsx, patient-record-panel.tsx, docs/USER_JOURNEY_TH.md |
| Single-document AI review | core-workspaces.tsx, backend/app/document_completeness.py and source-bound review controls |
| Four preparation profiles and watch limits | care-workspace.tsx, docs/AI_DRIVEN_CONTRACT_V1.md, docs/USER_JOURNEY_TH.md |
| LabClear source transfer and confirmation | labclear-review-panel.tsx, workspace.tsx, docs/USER_JOURNEY_TH.md and retained integration checkpoint |
| DR gateway controls | dr-review-panel.tsx, workspace.tsx, docs/USER_JOURNEY_TH.md; current entry label is **DR screening**, not the older prose label “Review with DR” |
| Administration | admin-workspace.tsx, backend/app/admin.py, docs/ADMIN_OPERATIONS.md |
| Portal and system operations | portal.tsx, operations.tsx, actual role map in backend/app/auth.py |

The guide does not infer unimplemented search or assignment controls from the
schema. Queue search is described as filtering loaded work. Generic task forms
do not claim claim/reassign/due-date functions. The Admin directory is described
as server-paged search, while sessions is explicitly a latest-200 projection.
Its row count is not substituted for the overview aggregate.

## Media identifiers and their intended use

Media files and hotspot coordinates are supplied by the integrating media
module. The content stores IDs rather than inventing image paths.

| ID | Intended illustration |
| --- | --- |
| login | Access/HIS sign-in explanation; no entered credential |
| workspace | Current workspace and queue navigation |
| patient | Wide patient/document reading panel with fictional data |
| documents | Current document/version workspace |
| review | Single-document completeness findings and reviewed-version controls |
| assistant | Prepared work, source evidence and selected workflow effects |
| labclear | Released source and separate review values |
| dr | HIS DR gateway image-set inspection before transfer; not receiver grading or inference |
| admin | Actual Admin directory/overview on desktop |
| adminMobile | Actual responsive Admin view |

The parent reported a current protected DR gateway capture using authored
synthetic eye images, without transfer consent, sending, preparing a new set or
model calls. That screenshot illustrates image-set inspection only. Access to
the receiver is conditional on a provisioned destination and confirmed import;
an existing selector entry is not proof of either.

No screenshot is claimed as captured or visually validated by this content task.
The parent must verify actual media provenance, readable captions, hotspot
accuracy, play/pause controls and reduced-motion behavior before publishing.
Animations explain steps; they must not issue product mutations or inference.

## Evidence boundaries retained in the guide

- The app is a synthetic development POC. The retained 38-domain/10-journey
  baseline is local evidence, not a new public-browser rerun or clinical
  effectiveness study.
- Single-document completeness and four-profile preparation use distinct
  workflows. Reading a page does not request inference; there is no silent
  cloud or mock fallback.
- A preparation profile does not broaden data access. Records readiness uses
  metadata only; the existing nurse role does not gain laboratory sources.
- Partial inputs, stale sources, failed/timeout/abstained/invalid outputs and
  unknown monetary cost retain their meaning.
- AI effects save human-reviewed drafts and selected tasks, not diagnoses,
  doses, clinical signatures, orders or result release.
- LabClear confirmation does not replace HIS source values, finish a HIS task
  or re-release a result.
- DR guidance separates source context, manual quality/draft review, grade
  confirmation, signing and model inference. Ten renamed MMRDR images remain
  held for laterality; they are not paired, assigned or analyzed by this guide.
- Public create/reset uses the ordinary 12-character password policy. No
  account password, session material or private provisioning input is included.
- Identity administration does not automatically grant clinical signing or
  host-wide backup/restore operations.
- Financial and stock actions preserve transaction and separate-approval
  boundaries. A request with an unknown outcome is recovered as the original
  request, not recreated with altered values.
- delivered_local, internal export and manually recorded response references
  do not establish actual external acknowledgement.

## Validation performed by this task

**PASS — content module evaluation and data-contract checks.** Node.js24.19.0
loaded the TypeScript module using built-in type stripping. Assertions checked
16 unique chapter IDs, 38 ordered/unique D01–D38 references, 101 chapter steps,
152 domain steps, nonempty prerequisites/completion/troubleshooting, valid
chapter-domain links and the ten agreed media identifiers.

**PASS — source/wording review.** Every domain reference was checked against
the inspected catalog fields/action labels; shared-core domains use their
authored React workspaces and operator guides. Consequential guards were
checked in actual clinical/ERP transactions rather than inferred from a button.

**PASS — diff whitespace check.** git diff --check returned zero.

**NOT_RUN — frontend integration, component tests, build, rendered media,
browser, production and clinical checks.** Those are separate integrator
responsibilities. No backend or live model test is required or claimed for this
data-only authoring task.

## Maintaining the guide

When a form, permission, transition, navigation label or connector boundary
changes, update the relevant chapter and domain entry together. Preserve the
DTO shared with the guide UI unless its consumers change in the same reviewed
revision. Recheck actual source controls and the media caption; do not silently
turn a proposed feature or an old screenshot into a current behavior claim.

Keep source data, screen captures and animation verification distinct. Add a
new screenshot only after checking that it contains no credential or real
patient data. A content or screenshot update never authorizes a new transfer,
model call or clinical action.
