# Clinical Workspace and Patient Record

Owner selection, 14 November 2026: Clinical Workspace (proposal 1) is the main
workspace; Patient Record (proposal 2) guides patient work; the Operations Desk
(proposal 3) loop mark is the shared CareBalance logo. This replaces the earlier
triadic layout, while retaining its three color anchors and existing workflows.

## Product contract

The home page prioritizes a real scoped work queue and details for the selected
item. Navigation and view controls remain quiet. Patient work keeps patient and
encounter identity visible while moving between records and documents. Login is
a separate full-size screen with the same brand, two actual account fields and
clear error recovery. Public login contains no patient or task previews.

English is used for primary navigation and view headings. Thai remains natural
for clinical records, explanations and form content. Neutral surfaces, readable
mixed-language typography and restrained borders carry the layout. Blue #1C4286
identifies primary actions; burgundy #861C42 draws attention to review needs;
green #42861C indicates evidence found, without implying clinical correctness.
No colored leading card stripes, decorative KPI cards, status-pill stacks or
fabricated charts are introduced.

The prototype's eight tasks, authors, documents and counts were authored visual
fixtures. They are not application records and must not enter the live database
or be displayed as live data. Application details come only from existing
authorized APIs. Missing fields are omitted or described honestly; a collection
limit must remain visible rather than being represented as a global total.

## Workflow boundaries

- Preserve local account/session/CSRF behavior and current permissions.
- Preserve all 38 domain destinations and typed forms, including roles that have
  more destinations than the limited test account.
- Keep exact task, patient and encounter routing, including same-patient visits.
- Reading a patient context does not grant registration or administrative access.
- Document revisions and source quotes retain their actual identity and version.
- AI provider selection, model pins and failure behavior remain unchanged.
- Human edits create a new action version; approval and commit remain bound to
  current context, version, hash, evidence and stable retry keys.
- Loading, empty, denied, error, pending, unsaved and recorded states remain
  actionable with keyboard and narrow-screen navigation.

## Research and provenance

The owner selected the combination after reviewing full-size dashboard/login
proposals researched on 14 November 2026. The original proposal archive is local
to the design workspace; competitor screenshots and fictional prototype records
are not shipped in the product. The following primary references informed
structure, not copied product assets or clinical claims:

| Reference | Applied observation |
|---|---|
| [Medplum Provider Tasks](https://www.medplum.com/docs/provider/tasks) | Task list and selected context can remain visible together. |
| [Bahmni Patient Dashboard 2.0](https://bahmni.atlassian.net/wiki/spaces/BAH/pages/5442240665) | Stable patient context supports document and visit work. |
| [Oracle Health patient panel](https://docs.oracle.com/en/industries/health/oracle-health-ehr/ehrfg/patient-panel.html) | Patient and encounter identity should persist during work. |
| [Linear design refresh](https://linear.app/now/behind-the-latest-design-refresh) | Reduce navigation weight while retaining useful information density. |
| [Attio record pages](https://attio.com/help/reference/managing-your-data/records/create-and-view-records) | A selected record preview can preserve the surrounding list. |
| [Primer DataTable](https://primer.style/product/components/data-table/) | Consistent columns, row rhythm and alignment support scanning. |

These are public documentation and visual references, not a comparative usability
study or a claim that this POC implements those products. Fonts retain their
individual OFL notices. The selected logo is the original loop path from proposal
3, not a competitor logo.

## Release evidence

The deployment report and evidence for this iteration are recorded separately
from the 13 November baseline. A source/build test does not establish browser,
public Access, model or clinical acceptance. Deployment updates only the dedicated
HIS application; the active database, file volume, accounts, connector and existing
Ollama service are preserved. A pre-update server backup and prior image support
application rollback without restoring over live data.

## Implementation checkpoint

The selected implementation is deployed as workspace-072a759f371d. Current checks
and phase boundaries are in [the release report](../RELEASE_CLINICAL_WORKSPACE.md).
Frontend25unit/76component/audit/typecheck/build, independent review, actual local
browser and a real-model human-review flow passed. Authenticated public browser
acceptance remains pending owner Cloudflare Access email verification. The earlier
public run and this local inference are not substituted for that pending check.
