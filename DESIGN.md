# CareBalance interface system

Locked to the user's triadic palette on 13 November 2026. This supersedes the earlier green and purple/yellow/orange interface directions. The application is an operational HIS workspace, not a marketing page.

## Color and type

| Role | Anchor | Usage |
|---|---|---|
| Primary | #1C4286 | Primary actions, current location, focus and navigable task titles |
| Review | #861C42 | Missing/unclear evidence, failed/rejected outcomes and work awaiting review |
| Verified | #42861C | Evidence found and recorded/verified outcomes; never a claim of clinical accuracy |
| Neutral | CSS semantic surface/ink tokens | Canvas, work surfaces, labels, tables and separators |

Every CSS color and font uses a root token; tints are derived for readable backgrounds. IBM Plex Sans Thai is self-hosted with its recorded OFL notice. Labels use the body face rather than technical monospace. Code, hashes and exact model identifiers retain monospace. Normal product-scale type and 4/8/12/16/24 spacing are preferred over display text.

## Composition

The shell keeps the permission-filtered fixed sidebar because the system has38 destinations. The main work region is capped and centered; mobile navigation becomes a focus-contained drawer, makes the underlying main inert and restores focus after Escape. Clinical context stays visibly separate from page content.

Home has one real task register with search and status filtering. Counters retain server-provided meanings. Task rows open the specific task, patient and encounter through URL parameters; the encounter must resolve against scoped records. Workload, recent records and workspace directory are secondary disclosures.

Shared domains use list/detail work surfaces, typed inline forms and state-specific commands. D22 retains immutable document revision reading/editing/attestation flows. D37 uses compact task/document intake, progressive proposal selection and parallel source/findings panels. Human review and commit actions remain beside the review, with detailed model/run history progressively available.

The interface has no marketing hero, decorative gradient, invented chart/KPI, fake result or automatic clinical action. Findings carry words and symbols as well as color. Source quotes prove containment, not semantic or clinical correctness.

## Context and transaction states

- Selecting a subject resets prior drafts/results through existing route/context boundaries.
- Visible proposals must match the selected patient/encounter metadata; unknown metadata fails closed under a selected context.
- Browsing authorized history without global context is read-only. Editing, approval and commit require both global IDs to match the bound proposal, and any selected task must match.
- Runs/results are resolved through scoped task identities because result DTOs do not carry direct patient/encounter fields.
- Busy, ambiguous network outcome and pending replay retain original operation keys. No provider or mock fallback was introduced.
- Rejected/recorded status is displayed directly; an artificial linear progress ribbon no longer suggests approval for terminal outcomes.
- Loading, empty, error, denied, disabled, unsaved, pending, confirmed and read-only states use existing real behavior.

## Verification

Read docs/design/TRIADIC_REDESIGN.md for exact source/evidence and retained failures. Visual quality uses the requested no-slop-ui rules and Hallmark app-screen guidance; backend authorization, data correctness and task truth take precedence over visual heuristics.
