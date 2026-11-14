# Patient panel release checkpoint

Date:14 November2026. Data: authored synthetic only. Public URL:
**[his.ai-cie.com](https://his.ai-cie.com)**, protected by Cloudflare Access and
the existing HIS account permissions.

The wide Patient panel, selected Home/Login and logo are deployed. This is a UI
checkpoint within the **active long goal**, which also includes a separate
CareBalance DR derivative and LabClear integration/theme work. Those integrations
are not implemented or accepted by the evidence in this report.

## Result and remaining acceptance

The main queue now opens a separate, wide patient record instead of requiring
the narrow right preview for reading. Users can select documents, read source
text, expand visits and continue into the existing document/review/visit
workspaces with exact context. The panel itself is read-only. Closing it restores
queue position and trigger focus. Explicit route/Login/logout navigation resets
the viewport. See [User journey](USER_JOURNEY_TH.md) and
[design contract](design/CLINICAL_WORKSPACE.md).

Final frontend **25 unit /91 component /3 audit cases, typecheck and build PASS**.
Active runtime matches **214 source files /17 built assets**. Origin asset hashes,
Access gates, app-only activation and prior state preservation pass.

The parent relayed the earlier `selected_ui_review` agent's final91 scroll-only
review PASS and zero source/dist drift; that reviewer did not rerun tests or the
browser, and no separate durable final91 review receipt was available here. The
documentation closeout directly rechecked58 frontend source/dist hashes with zero
drift and compared48 backend source files between the89 and91 snapshots, all
unchanged. [Direct source/phase check](../evidence/research-ui-release/final91-source-phase-check.json).

A fresh public Chrome document → real Typhoon → human editv2 → approve → commit →
reload workflow passed on the preceding89-component wide-panel candidate. Its
exact result passed all16 read-only server checks again after the final
scroll/focus-only update. The final rendered navigation/Login/logout scroll smoke
passed. **Interactive reopening of the persisted proposal after the final swap
remains NOT_VERIFIED**: click/key did not select it. The current browser URL then
could not be verified, ending that browser attempt. No cause was established;
current server result verification remains PASS. Do not promote the earlier
interactive workflow to an unexecuted final91 interactive check.

## Exact release phases

| Phase | Candidate and checks | Actual evidence and boundary |
|---|---|---|
| Initial selected UI | image`workspace-072a759f371d`;25 unit/76 component | Local browser15 observations and one local real-model/human persistence run. Access was pending at that checkpoint. [Initial report](RELEASE_CLINICAL_WORKSPACE.md) is historical. |
| Wide patient record | image`workspace-86b174ff10c5`;25 unit/89 component | Local panel8 observations; actual protected public desktop/mobile panel and fresh public real-model/human v2/commit/reload workflow. [Local panel receipt](../evidence/research-ui-release/patient-panel-local/browser-acceptance.json), [public readback](../evidence/research-ui-release/patient-panel-public/public-workflow-readback.json). |
| Final scroll/focus follow-up | image`workspace-167d14addf47`;25 unit/91 component/3 audit cases | Only App viewport reset/focus and focused tests change from the preceding source phase. Backend/AI/transaction guards are unchanged. Active source/assets, preservation and earlier public result are checked again. [Frozen checks](../apps/web/evidence/patient-record-panel-scroll-20261114-final/checks.json), [phase comparison](../evidence/research-ui-release/release-checkpoint.json). |

The local synthetic model run on Windows is **not** the later public model run;
its records were not copied into the server database. Component tests use jsdom
and authored HTTP doubles. Audit tests use isolated legacy doubles. None of those
receipts alone demonstrates a public browser workflow, PostgreSQL acceptance or
clinical effectiveness. Original full-system38-domain L2/10-journey L3 local
acceptance was not rerun for this UI checkpoint.

## Patient journey observations

On actual Chrome at1536px, the earlier right preview was330px wide. The public
Patient panel is1120px wide, with790.4px for source reading. At390px mobile width,
the panel is390.4px and source area356.8px; there was no page horizontal overflow.
Mobile document selection uses the native selector. These are point-in-time
rendered observations and owner feedback, not a usability study.

- Queue patient links and Open patient record open the separate dialog.
- Document selection stays inside the panel. Visits expand into a list;
  Open visit continues in the existing visit workspace. There is no encounter
  dropdown inside the panel.
- Open document and Open review preserve exact patient/encounter/document/task
  identities. Editing, inference, approval and commit remain in their existing
  authorized workspaces.
- Close/Escape restore the queue and keyboard focus. Loading, empty, denied and
  error states remain distinct; close/reopen retries a failed panel load.
- Parent-observed final rendered scroll checks: navigationY115.2→0,
  logoutY2.4→0, visible Login brand top27.6px and signinY0. Signin returned to
  the original D37 route; this is not a claim that signin always opens Home.

Actual public Chrome captures:
[desktop panel](../evidence/research-ui-release/patient-panel-public/patient-panel-desktop.jpg),
[new document](../evidence/research-ui-release/patient-panel-public/patient-panel-new-document.jpg),
[mobile panel](../evidence/research-ui-release/patient-panel-public/patient-panel-mobile.jpg),
[committed result metrics](../evidence/research-ui-release/patient-panel-public/ai-committed-metrics.jpg)
and [final Login](../evidence/research-ui-release/patient-panel-public/login-final-desktop.jpg).
Local panel images are retained separately in`patient-panel-local`.

## Public real-model result

The owner completed Access verification. The limited test01 account then used
the visible public React UI to create the synthetic document and task, open the
exact review, run the pinned existing Typhoon once, edit the proposal into
version2, approve that version, commit and reload.

| Record | Exact value |
|---|---|
| Document | `56b34d6a-e16f-4e73-b34b-a839ea25d73f` |
| Source revision | `618610a6-3d5f-4fc0-a4df-5ed7fe200512` |
| Task | `1e5bda27-e154-4415-b48d-97e0ed96ec20` |
| Inference run | `9b797df1-18b5-4537-b036-b37cf8d337ca` |
| Proposal | `1715af20-6275-43a3-bfbb-08ce6ffec70f` |
| Committed result | `64d8a1ae-958c-4c33-a4e8-fa222c1e8448` |
| Approved action version/hash | `2` / `73bd30484fb8b6c8f25a443c91b59bc85283bd95be392ea3eada5d667cd40483` |
| Measured elapsed/usage | `11563ms`;424 input /134 output tokens; cost`null` |
| Existing model/engine | Typhoon2.1-Gemma3-12B Q4_K_M /Ollama0.12.6 |

The model checklist found four present items and a missing plan. Source quotations,
exact source revision/context, changed human action hash, current-version approval,
canonical result, stored idempotent replay, one attempt/proposal/result and one
committed audit event pass the16 read-only repeatable-read PostgreSQL checks.
See the [public workflow receipt](../evidence/research-ui-release/patient-panel-public/public-workflow-readback.json)
and [repeat after final activation](../evidence/research-ui-release/deployment/scroll-reset/prior-public-workflow-readback.json).
No additional inference was performed for the scroll-only follow-up. Cost`null`
means unmeasured; it is not zero. One synthetic run is not a latency guarantee,
capacity benchmark or clinical/product evaluation.

## Final runtime and preservation

| Binding | Value |
|---|---|
| Image | `his-poc-server:workspace-167d14addf47` |
| Image ID | `sha256:56821a7a82ae714f7bfc039ef82e35ad51c4d0b5f91d89c5d5d816de8cb9210b` |
| Snapshot SHA256 | `167d14addf47841efa40298098aa1552761518eee3c99acd2e329fde3da16d87` |
| Active source/build |214 source files /17 assets; zero mismatches |
| Immediate rollback image | `his-poc-server:workspace-86b174ff10c5` |

The214 active source hashes match the frozen deployment snapshot. Later
`config/runtime_inventory.json` changes update reporting metadata and are
intentionally outside that active image. Current frontend source/dist still match
the final91 receipt exactly; the source-phase check lists this single expected
metadata difference explicitly.

Fresh private database/files backup preceded replacement of only the application.
All180 preexisting session rows,109 nondecreasing table counts, test01 account/scope,
three selected committed results and the one stored file were preserved. These
counts describe the preactivation/postactivation comparison before further browser
actions. Database and connector container identities were unchanged. All four
endpoints remain on loopback; connector reports four HA connections. No database
restore, seed, account reset, connector restart, DNS/Access change, new model
installation or unrelated service mutation occurred for this final activation.

Receipts:
[activation](../evidence/research-ui-release/deployment/scroll-reset/activation.json),
[preservation13 checks](../evidence/research-ui-release/deployment/scroll-reset/postactivation-preservation.json),
[runtime214/17 hashes](../evidence/research-ui-release/deployment/scroll-reset/runtime-source-binding.json),
[origin7 hashes](../evidence/research-ui-release/deployment/scroll-reset/origin-assets.json),
[Access5 probes](../evidence/research-ui-release/deployment/scroll-reset/public-access-boundary/access-boundary.json).
Anonymous probes used certificate-verified HTTPS without following redirects or
retaining cookies/assertions. The invalid assertion was rejected at Access.

Rollback selects the previous immutable image and recreates only app, retaining
database/files. No rollback was executed. Follow [deployment operations](DEPLOY_DR_TRAIN.md)
and take a fresh backup/state observation before a future change. A Git source push
does not deploy an image; source publication is the parent integrator's separate
step. Historical receipts, diagnostic failures and the initial Access-pending
record remain available with their original phase and scope.

## Continuation

Documentation closeout directly ran the repository`.venv` static package
consistency checker and the **unstaged tracked-file** `git diff --check`, both
PASS. That whitespace command could not inspect the then-untracked new license
files. After staging, `rtk proxy git diff --cached --check` returned **FAIL** for
the upstream trailing space at line21 in four verbatim OFL files:
`apps/web/public/fonts/{anuphan,instrumentsans,manrope}-OFL.txt` and
`docs/branding/manrope-OFL.txt`. The parent integrator accepted this specific
vendor-license whitespace exception. Their exact bytes and frozen SHA256 hashes
are preserved; no whitespace was removed from the licenses. The staged command
remains a recorded FAIL with that known exception, rather than a clean PASS.
Relative document links and
JSON parse passed; a scoped text scan found no private key, JWT, GitHub token or
the owner-requested plaintext test password in reviewed release text. This is not
a binary screenshot audit or a repository-wide secret guarantee. See
[documentation checks](../evidence/research-ui-release/release-documentation-checks.json)
and [retained initial link failure/repair](../evidence/research-ui-release/release-documentation-link-repair.json).
No application tests, browser action, inference, deployment, package ZIP or source
stage/commit/push was performed by the documentation closeout agent.

Re-establish the authenticated browser's current URL, then open the exact retained
proposal and inspect version2/result to resolve the final interactive check. No
extra inference, seed or account reset is needed for that inspection. A current
server readback is already PASS; do not claim the browser selection passed until
it is observed.

Continue the owner-authorized long goal: establish the separate CareBalance DR
derivative, preserve the original DR project, connect LabClear and adapt its theme
with explicit identity/context/result contracts. Those tasks require their own
implementation, review, source/runtime binding and end-to-end evidence. This UI
checkpoint does not close that goal or certify production/clinical readiness.
