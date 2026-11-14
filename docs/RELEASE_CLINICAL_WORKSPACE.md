> Historical initial selected-UI checkpoint: image072 /76 component tests.
> The current wide-panel/final91 release and later public workflow are recorded in
> [RELEASE_PATIENT_PANEL.md](RELEASE_PATIENT_PANEL.md). The original report body
> below is retained unchanged, including its then-pending Access status.

# Clinical Workspace deployment — 14 November 2026

The selected UI is deployed at https://his.ai-cie.com behind the existing
Cloudflare Access application. Home follows Clinical Workspace (proposal1),
patient work follows Patient Record (proposal2), and Login/navigation use the
original Operations Desk loop logo (proposal3). This release preserves backend
code, schema, account permissions, AI provider selection and review transactions.

## What changed

- Scoped task register and real document preview on Home, with readable English
  primary headings and Thai record content.
- Patient context, horizontal navigation and broad document/source panes.
- A dedicated Login composition with public neutral artwork, the selected logo
  and existing account/error behavior.
- Self-hosted Manrope, Anuphan and Instrument Sans WOFF2 with individual OFL
  notices. No competitor assets or prototype patient/task fixtures are shipped.
- Document preview now reads the actual top-level DTO. Document lists/details
  match the selected patient and encounter even in the all-encounters view.
- Context selectors and D01/D03 context actions canonicalize URLs, clear stale
  record/task bindings and survive reload/history.

## Exact candidate and activation

| Item | Verified value |
|---|---|
| Source snapshot SHA256 | 072a759f371d7c77d50edb5ce1bb5fe14907ba7ba6889b6d04e4bf027aff19bf |
| Image | his-poc-server:workspace-072a759f371d |
| Image ID | sha256:cd6f108817aa65663c7bc2842bcc40242356b15924015a7a266e62a1e5aae211 |
| Candidate binding | 212 source files and17 dist assets match |
| CSS / JS | index-3ptj9r2B.css / index-DMoPMKHs.js |
| Rollback image | his-poc-server:triadic-778ba97bf46f |

A fresh private server database/files backup preceded replacement of only the
app container. The database and connector container IDs did not change. All109
table counts, one exact file, test01,178 prior sessions and two selected prior
real-model committed results were preserved. No restore, seed, account reset,
schema change, DNS update or shared Ollama restart occurred.

All four private listeners remain loopback-only. Readiness confirms migration0002
and no-store. Seven origin assets return200 with body hashes matching the frozen
build. Five unauthenticated HTTPS paths still redirect to Access, including an
invalid assertion. See [deployment receipts](../evidence/research-ui-release/deployment/)
and [public boundary](../evidence/research-ui-release/public-access-boundary/access-boundary.json).

The earlier candidate snapshot425ea647... was superseded before transfer/build
when final context callbacks were repaired. Its retained phase receipt prevents
confusing it with the activated candidate. Later root documentation/evidence edits
do not change the frozen application; runtime/source and dist binding are explicit.

## Executed acceptance and limits

- Frontend25 unit /76 component tests,3 audit cases, typecheck and build PASS:
  [final checks](../apps/web/evidence/research-ui-20261114-final/checks.json).
- Independent read-only source/hash and actual desktop Login/Home/Patient image
  review PASS: [review receipt](../evidence/research-ui-release/independent-review.json).
- Actual local browser15 observations PASS, including mobile/keyboard, context
  switch/reload/history and an end-to-end real-model workflow:
  [browser receipt](../evidence/research-ui-release/browser-local/browser-acceptance.json).
- Read-only PostgreSQL verification of that local workflow PASS16 checks:
  [exact readback](../evidence/research-ui-release/browser-local/local-workflow-readback.json).

The new synthetic run is bf08ea07-0771-49e7-b179-5e593a6e59d1, result
9fb308fb-ac85-4319-9e8b-772d1e6b97f0. Existing pinned Typhoon/Ollama returned four
present findings and one missing plan in11623ms,413 input/133 output tokens,
monetary cost null. Human editing created immutable version2; approval/commit
matched source/context/action hashes. Exactly one inference attempt/proposal/result
and commit audit were confirmed. Opening the task again retained the committed
proposal and disabled repeat actions. This run used the local Windows database,
which remains separate from the deployed server database.

**Authenticated public browser acceptance for this iteration is NOT_RUN.** The
current browser awaits the owner's allowed-email verification in Cloudflare
Access. The asynchronous handoff remains pending; local acceptance and the prior
13 November public run are not substitutes. Continue from
[the exact pending checkpoint](../evidence/research-ui-release/public-authenticated-pending.json)
after verification. Do not reset test01, reseed or restore the active database.

The38-domain/J01–J10 baseline was not rerun in this UI iteration. Clinical
effectiveness, other external adapters and throughput remain outside these checks.
Use [the deployment runbook](DEPLOY_DR_TRAIN.md) for image-only rollback.
