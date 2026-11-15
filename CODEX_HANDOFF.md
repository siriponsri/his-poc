# Codex handoff — illustrated User Guide and Admin acceptance

## Illustrated in-app User Guide — 15 November 2026

Status: DEPLOYED_AND_GUIDE_ACCEPTED for the synthetic protected POC.
Runtime source 65c5bc5 / image 92166e35 / schema 0005 serves /guide. The guide
opens from login, the workspace header or sidebar; static help remains readable
without an HIS session after the existing Cloudflare Access gate.

It includes 16 chapters/101 task steps, 38 domain references/152 working steps,
11 exact synthetic screenshots and 10 paused-by-default explanatory walkthroughs.
Search, shareable chapter/domain links, role-oriented navigation, image zoom,
keyboard scrolling and mobile contents return are implemented. Guide controls
do not submit clinical work, change roles or request model generation.

PASS on base f962196: 31 frontend units and 195 mounted cases (20 guide + 4 shell).
Final source 65c5bc5 changes one heading CSS rule; its typecheck/build, independent
narrow review and protected desktop/mobile heading recheck passed. Content/media
validation and the remaining native reading checks passed separately. Protected acceptance and current runtime are recorded separately in
[User Guide release](docs/RELEASE_USER_GUIDE.md) and
[browser evidence](evidence/user-guide-20261115/browser-acceptance.json).
The Admin account, workflows, AI source/configuration and specialist services
remain preserved. This is a guide release, not new clinical/model effectiveness.


## Resume checkpoint

Current deployed application source: `65c5bc517b0b5905355ebc2a161c93635a9a7c97`.
The later documentation/evidence commit does not require another deployment.
The final named app image begins `92166e35`; schema remains 0005. Use the latest
heading-followup witness in [the release report](docs/RELEASE_USER_GUIDE.md).
The server deployment directory is not a Git checkout. Recheck current identity
before future server actions; preserve current rows, uploads and unrelated work.

The User Guide and Administration requests have reached protected browser
acceptance. Product proposals remain proposals in
[the review](docs/PRODUCT_REVIEW_20261115.md); no new clinical evaluation, model
installation or broader deployment is implied by this checkpoint.

## Retained Administration release — 15 November 2026

Status: DEPLOYED_AND_ADMIN_ACCEPTED for the named synthetic POC. Runtime source
74795e2 / immutable image416fbe75 / schema0005 is ready behind existing Access.
The requested admin account was privately provisioned and normal login passed.
Dedicated /admin covers users, memberships, sessions and security activity,
without initial clinical-signing or platform-operator grants.

Local checks passed38PostgreSQL18.6 cases,171mounted frontend checks,31unit
checks and typecheck/build. Protected-browser acceptance covered login/default
landing, search, four sections, create-dialog reading/close and desktop/mobile
layout. An initial390px overflow was retained and repaired with one CSS rule;
the final live mobile readback passed. No public user-management mutation was
performed beyond the separately evidenced private account provision/authentication.

The same AI source/configuration and prior6runs/8revisions/5decisions/7effects
remain; this Admin release issued no model generation. Historical broad-domain,
AI and specialist evidence below retains its original scope.
See [Admin release](docs/ADMIN_RELEASE_20261115.md),
[runtime proof](evidence/admin-20261115/final-runtime.json),
[browser acceptance](evidence/admin-20261115/browser-acceptance.json) and
[product review](docs/PRODUCT_REVIEW_20261115.md). The roadmap is proposed work.


## Retained AI-driven acceptance before the Admin release

Status: DEPLOYED_AND_APPLICATION_ACCEPTED for the named synthetic POC scope.
Runtime source286f391 / immutable image9afd73f2 / schema0005 is deployed behind
the existing Access policy at https://his.ai-cie.com. Login, wide Patient record,
realistic fictional patients, LabClear and the separate DR derivative remain.
Operations opens in2D; explicit3D rendered on the protected URL and its room
opened the same saved visit. The3D scene is illustrative, with no staff tracking.

The foreground cron-owned assistant guard was observed from fresh SSH at17:57
UTC, with matching PID/startticks/cgroup/config/privateENV/image. The exact owned
one-off was removed and persistent reboot approval recorded. No reboot was run.
This is separate from actual inference: six normal-application Typhoon calls
completed with bound terminal evidence, using existing clinician/nurse/
registration/laboratory roles and no permission changes. Four preparation
profiles passed source-fidelity review. The original nursing test-only input was
preserved unapplied; one explicitly reviewed reserve call used a better authored
synthetic handover. No automatic retry, cloud fallback or held-image inference.

Five accepted decisions saved seven effects: two draft documents, two new
follow-up tasks and three links to existing review tasks. Human edits remained
new revisions; actual identical-key HTTP replay for nursing/records/laboratory
created no duplicate effects. Records used metadata only; nursing had no lab
source access. Nine actual role/scope reads passed expected403/404/metadata
boundaries. The protected public browser covered one visit: queue → evidence →
full omitted note → explicit demonstration edit → apply → full reload. Other
role workflows were normal authenticated production API checks, not separate
public-browser role acceptance.

An unchanged records watch caused zero automatic runs during its observed scan
window. One explicit authored source revision caused one new run; its reviewed
effect reused the original records task. The watch is paused with count1.
The source change intentionally leaves earlier visit/records artifacts stale;
saved old drafts/evidence remain. Page reads,2D/3D navigation, apply and replay
do not dispatch inference. Runtime app/worker remain enabled for explicit use.

Read-only18:12 preservation passed all old126HIS/2LabClear/10DR table rows, source
files, legacy configuration and non-app service identities. HIS additions are
explicit test records, not overwritten baseline rows. Historical InferenceRun9
(3REAL +6mock) and nine results remain separate from the six new AssistantRuns.
The original DR repository and LabClear owner edits remain preserved; ten renamed
MMRDR images remain held for laterality as the owner requested.

Evidence: [application acceptance](evidence/ai-driven-root-20261114/application-acceptance.json),
[deployment](evidence/ai-driven-root-20261114/deployment-readback.json),
[public screenshots](evidence/ai-driven-public-20261114/),
[release guide](docs/RELEASE_AI_WORKSPACE.md).
Final local source checks passed187 disposable PostgreSQL18.6 cases,156 mounted
frontend checks,31unit checks, typecheck/build; these are not a rerun of all38
domains. The older broad-suite failure and isolated resolution remain retained.
Two neutral infrastructure calls and five direct qualification calls are separate
from application calls; that direct budget is exhausted. Application trial used6
of7, including one source-correction reserve; no remaining trial call is automatic.

Limits: measured provider times50.579–56.381s, not a benchmark/SLA; monetary cost
is unmeasured/null. Outputs largely copy included short notes or select title/DOB
facts. Visit/nursing compact inputs omit records and require full-chart review.
This does not establish clinical effectiveness, measured staff-time savings,
all38domains using realAI, MedGemma27B/DR inference or host-reboot acceptance.
Direct fixture evidence, actual application effects and clinical validation must
remain distinct. Current API/DDL reference is docs/integrations/contracts-0005;
the historical contracts/v2 export is preserved separately.

## Earlier DR checkpoint at 12:04 UTC

Long goal ACTIVE. The named public deployment is now HIS
`his-poc-server:workspace-074aa8f8a0b2` / image
`sha256:a30f5e9d1e9284942343098423b0bfe56e27c91325d84fb68b86b3d4c22159f0`,
ready on `0004_dr_screening_bridge`; DR
`his-poc-dr:source-05476e8f5ebb` / image
`sha256:2891650421e89546783d9c3a268dbdc8f6fcef3ebbe84500163be6f6c894d2e5`,
schema1; LabClear remains `source-c1944c772e87` / image
`sha256:d02a78be86e67d8fc64f5133ceb5a07ab2270b4e97ad44f4fa518748da539b6f`.
Each receiver has a dedicated PostgreSQL database and loopback listener. The
original non-app containers/configurations, all112 legacy table row hashes,
files/sessions, all9 committed results/3 selected hashes and inference9 were
preserved. Fresh backup/isolated restore passed112 tables/one file at11:07Z.
No production seed/reset/restore or new signing/grade grant occurred.

### Exact current checkpoint and pending gates

- New owner steering: realistic FICTIONAL Thai patient names, age/sex/HN context
  and coherent clinical values replace literal numbered synthetic labels.
  Normal patient PATCH supports versioned/audited name/DOB/sex; existing HN
  identifiers remain immutable except normal creation of a new patient. Planned
  six-patient fictional dataset/metadata/UI enhancement is NOT_IMPLEMENTED;
  normal PATCH source support was investigated but no names/demographics have
  changed. Never introduce real patient data. The sealed DR source-set snapshot
  binds IDs/source versions/hashes, not live demographics; preserve the same
  patient IDs/pseudonym/source binding and test the live label after amendment.
  Record intentional Patient row/version/name/DOB/sex exceptions AFTER the
  existing preservation checkpoint. Do not claim all original row hashes remain
  unchanged after those authorized edits. Preserve all9 committed AI results,
  source files, memberships/scope and original source snapshots.
- HIS source main `ac63879e166c41c65b96f75a3ed22408e97bc11f` was pushed;
  current documentation changes are not yet committed.245 runtime source inputs
  match the deployed image. The derivative stays local/no remote at main
  `d8a2d9b6a21360e0dff3b4aeb97ea4c2692d225f`;191 inherited backend hashes match.
- Final human-label frontend manifest
  `34fd361069b3af61c789c7398a49a052feef736dc49303fd5866794f9752d079`
  static v2 refresh PASSED at2026-11-14T12:04:20Z. All3 databases/files matched
  exactly; all59 non-app container IDs, exact registry bytes/UID10001/mode0600
  were preserved and10 authenticated assets verified. The first attempt failed
  on missing parent-directory preparation before dispatch; retain that reconciled
  failure separately. Final label-only public browser smoke is NOT_RUN: physical
  Escape stopped Computer Use before new-bundle reload. Do not resume that
  stopped surface within the same turn or infer an owner pause of the goal.
- Final DR evidence:522 unique-case composite coverage, with521 full-run passes
  and one retained native30-second timeout; the unchanged isolated2-case rerun
  passes. Main76 focused plus UWF2/typecheck/build pass. This is not522 passes
  in one full execution. HIS77/receiver37 PostgreSQL and HIS25/135/3/build pass.
- Earlier public7c76 actual native-Chrome manual journey passes. It must not be
  promoted into the final34fd rendered acceptance without the pending smoke.
- Finish final label-only public browser smoke, then implement and qualify the
  fictional-data UX extension. Static/preservation proof is complete. Update
  exact intentional-change exceptions and
  all evidence links, commit/push authorized HIS docs/main and perform the final
  goal audit. Do not close the goal merely after the DR UI gate or publish the
  licensed DR derivative. No new inference is needed to prove static labels.
- At this checkpoint the new documentation/contracts/evidence are uncommitted;
  there is no new clean-checkpoint commit/push. HISmainac63879 remains the last
  source publication. Root owns the eventual reviewed checkpoint publication.

### Protected public browser and persisted record

The coordinator used the owner-authenticated native Chrome, with its own binding
`de1ab8b3-299f-4276-8b01-98dff797d993`, source set
`c2186190-b0d6-477c-92c4-37f6fa631b3f` and workspace
`cb-9b95bbb28262d356b9d03faafc2cb866`. Explicit consent showed both authored
640x480 originals, followed by left-eye manual quality acceptance, checked
patient/eye confirmation, unsigned draft save, full Chrome reload and explicit
"This draft has not been signed" check. Signing stayed disabled. Saved notes:
`CareBalance public browser DR integration check 2026-11-14; authored synthetic draft.`

Public-safe [read-only proof](evidence/integrations/public-dr-20261114/public-browser-readback-20261114T115240Z.json)
confirms receiver left revision3/PRELIMINARY/unsigned, quality and confirmation
by the verified HIS session, one read receipt/UNAVAILABLE freshness, exact notes
and unchanged original bytes. D11 left
`4377f0e6-4117-4a9d-961a-866fd5d34136` and right
`2658f896-6589-4dcb-b634-1382b34d3e57` remain version6. Review task
`d9583d21-b6c2-41f6-a0eb-4478c5baecec` remains OPEN; acquisition tasks are
complete; DR grants0/inference9/pending mutations0. A separate CLI-owned
authenticated asset proof used its own session/binding, without extracting
browser cookies and without changing clinical case hashes.

Ten public-safe deployment/backup/compatibility/migration/receiver/canonical/
browser-readback/static receipts and the reconciled initial failure are indexed
at [public-dr-20261114/receipts.json](evidence/integrations/public-dr-20261114/receipts.json).
Private credentials, browser cookies and raw dumps are excluded. This index
explicitly leaves final label-only rendered smoke and fictional data work open.

Current schemas are documented separately at
`docs/integrations/contracts-0004/manifest.json`:142 paths/120 modeled tables,
121 operational including Alembic. Keep baseline contracts/v2 as historical
image inputs. LabClear source/theme76 tests and bounded browser checks pass;
actual mobile width355/requested390,18 owner-modified file hashes unchanged.
The separate existing LabClear Render deployment is outside this activation.

Ten owner-renamed MMRDR images remain HELD_FOR_LATERALITY with unknown eyes,
untouched and unpaired. No clinical registration/transfer/model call follows
the owner's source attestation. Original DR source/Git/runtime are preserved.
Operations must layer server.env, labclear.env, dr.env and all three reviewed
overlays; base-only startup and old hardcoded0002 helpers are unsuitable.

## Earlier private/public-LabClear checkpoint history

The text below retains the preceding checkpoint and its dated identities.
Current deployment, publication and remaining gates are defined above.

Latest exact resume point: [DR_BROWSER_CHECKPOINT_20261114.md](docs/integrations/DR_BROWSER_CHECKPOINT_20261114.md).
Private Linux12 checks, same-DB compatibility rollback/candidate restore and the
manual-quality image upgrade pass. The coordinator recovered the native Chrome
surface in a later continuation and verified authenticated public Home. This
does not establish public DR acceptance. Private browser draft persistence after
reload, limited permissions, mobile390 and exact return were executed. Final
small frontend UX refinement is under qualification. Long goal stays ACTIVE.

DR checkpoint: [DR_RELEASE_20261114.md](docs/integrations/DR_RELEASE_20261114.md).
HIS77/receiver37 plus2 independent quality checks/prior full DRfrontend514/
HIScomponents135/schema121 pass; LC44 plus62 subtests and native legacy DR79
pass. Current private images are HIS074aa8f8a0b2 and DR05476e8f5ebb; exact IDs
are in the release checkpoint. LC UI rollback0004-2c88 is rehearsed on the same
shadow DB. No public04 migration/DR activation yet. Main integration/rebuild,
fresh production backup/restore and public acceptance remain required.
Ten owner-renamed MMRDR JPEGs are held for laterality per explicit owner choice;
no pairing, registration, transfer or model call. Exact local bytes are retained.

Historical LabClear deployment milestone: candidate5328 verifies231
source files/17 assets with25 unit/117 component/3 audit cases/build PASS.
Private LabClear two-DB and actual browser round trip passed. Final5328 is now
active on migration0003 with a separate ready receiver:109 legacy counts,
181 sessions, three selected results/file/account preserved. Actual backup
restore passed. Public browser source6 to reviewed7 confirmation/reload/read-only
reopen/mobile PASS; exact receipts under evidence/integrations/public-labclear-20261114.
Operations MUST layer server.env then labclear.env with base+receiver overlay;
base-only selects the old image. See ops-activation-runbook.md in deployment evidence.
DR derivative at C:/Users/User/Desktop/myProject/carebalance-dr-screening is
on feat/carebalance-his-bridge after qualified theme main eacdef0 and doc
commit a9932be. Original DR is excluded. Bounded receiver implementation ACTIVE;
no live retinal inference. Read [integration checkpoint](docs/integrations/VALIDATION_CHECKPOINT_20261114.md) and its
linked exact receipts. Do not close the goal while DR/BFF/public work remains.

## Subsequent publication and browser readback

UI checkpoint `1e77901` was committed and pushed to main. A later authenticated
Chrome inspection of `/assets/index-YkkpA1iL.js` successfully opened the retained
version2 proposal, matched its action hash/source checklist and verified disabled
edit/approval/commit actions, with no new inference or source writes. See
`evidence/research-ui-release/final91-public-reopen/acceptance.json`. This resolves
the earlier NOT_VERIFIED saved-proposal selection item below. The earlier full
real-inference journey remains89-phase evidence. The integration goal is active;
gateway/receiver work has since reached the private validation checkpoint above;
its public deployment is governed by the separate current receipts.

## Historical UI checkpoint — 14 November 2026

Work in C:/Users/User/Desktop/myProject/his-poc. The long goal remains ACTIVE:
separate CareBalance DR derivative based on dr-support-screening-poc, preserving
the original, plus LabClear connection and authorized source/theme adaptation.
Those integrations are not implemented by this UI checkpoint. Parent owns the
integration plan/source work and publication; this handoff does not imply a push.
At documentation closeout, Git HEAD was8681f32446cd3e4b92b611204f16462167f0755a
with shared uncommitted UI/docs/evidence work. Deployment is a working-source
snapshot rather than that commit. Parent must record the later publication SHA
after controlled staging/commit/push; no source publication was performed here.

The selected Clinical Workspace Home/Login, Patient Record full workspace,
Operations Desk logo and wide read-only Patient panel are deployed as
his-poc-server:workspace-167d14addf47. Snapshot SHA256:
167d14addf47841efa40298098aa1552761518eee3c99acd2e329fde3da16d87.
Image ID sha256:56821a7a82ae714f7bfc039ef82e35ad51c4d0b5f91d89c5d5d816de8cb9210b.
All214 source files and17 built assets match the final frozen candidate. Fresh
backup/app-only replacement preserved109 table counts, one file, test01,180 prior
session rows and three selected committed results. DB/connector containers and
the existing Ollama/Access/DNS were unchanged. Origin7 hashes and Access5 gates pass.

Frozen frontend:25 unit/91 component/3 audit cases/typecheck/build PASS, receipt
apps/web/evidence/patient-record-panel-scroll-20261114-final/checks.json.
Earlier76/89 component phases are historical; do not promote their browser checks
to an unexecuted final91 interactive test. Only App viewport/focus handling and
focused tests changed between the89 public workflow and91 final image; backend,
AI/provider and source/version transaction guards are unchanged.

Public Chrome test01→Home patient link→wide panel→Open document→fresh synthetic
document/task→Open review→real Typhoon→human edit v2→approve→commit→reload PASS on
the89-component image. Run9b797df1-18b5-4537-b036-b37cf8d337ca,
result64d8a1ae-958c-4c33-a4e8-fa222c1e8448;11563ms,424input/134outputtokens,
costnull. Exact16 read-only PostgreSQL checks PASS before and again after final
image activation, including one attempt/proposal/result and approval/action hashes.
See evidence/research-ui-release/patient-panel-public/public-workflow-readback.json
and deployment/scroll-reset/prior-public-workflow-readback.json.

Final rendered navigation scrollY115.2→0, logoutY2.4→0, Login logo top27.6 and
signinY0 were observed by the parent in authenticated Chrome. Final interactive
persisted-proposal reopening is NOT_VERIFIED: click/key did not select the item.
No cause was established. Browser work stopped when the current Windows Chrome
URL could no longer be verified; do not infer an app failure or success from that
automation boundary. Re-establish current URL, open the exact persisted proposal
and inspect its version2/result before claiming final interactive acceptance.
No extra model call or account reset is needed just to inspect the retained result.

Local browser15/real-model11623ms413/133 evidence and local panel8 observations
remain separate from public evidence and were not copied into the server DB.
The initial072/76 deployment Access-pending receipt is retained as superseded
history; the owner subsequently completed Access and the public flow above.

Read [release report](docs/RELEASE_PATIENT_PANEL.md),
[user journey](docs/USER_JOURNEY_TH.md) and [operations](docs/DEPLOY_DR_TRAIN.md).
Documentation closeout [checks](evidence/research-ui-release/release-documentation-checks.json)
record actual static package consistency, relative links, JSON parse, scoped text
secret review and git whitespace checks. Direct frontend source/dist hashes pass
with zero drift; all48 backend sources match between89 and91. The reporting-only
config/runtime_inventory.json update intentionally differs from the frozen image.
Rollback selects prior imagehis-poc-server:workspace-86b174ff10c5 and recreates
only app, preserving DB/files. No rollback has been executed.

The original38-domain L2/10-journey L3 local synthetic baseline below was not rerun
for this UI checkpoint. External/clinical/product effectiveness remain unverified.
No passwords, cookies, Access assertion, private env or tunnel credential belongs
in source/evidence. Publication and deployment are separate actions.

## Historical deployed state — 13 November 2026

The owner resumed and authorized the named synthetic deployment. https://his.ai-cie.com is active behind exact-host Cloudflare Access. dr-train root /home/chaw/his-poc is a snapshot runtime, not a Git checkout. Dedicated Compose project his-poc-server uses app127.0.0.1:18080, DB127.0.0.1:15432 and connector metrics127.0.0.1:20331; existing private Ollama11434 is unchanged. The Windows source database/files remain independent.

Final image his-poc-server:triadic-778ba97bf46f has48 runtime-source and21 built-asset hashes matching the reviewed frontend/backend. Original109 table counts/one file and prior real result were preserved; final replacement retained test01 and178 prior sessions. Source publication does not automatically deploy.

Latest frontend25 unit/69 component, audit/typecheck/build,13 actual responsive observations and independent review PASS. Public browser test01→D22synthetic document→D37real Typhoon→human editv2→approve→commit→reload PASS; read-only server verification confirms one attempt/result. Run63506882-333c-479c-992e-027b991c836a took10414ms,422input/136outputtokens,costnull. Result ef4e9f7e-e0b2-473e-ab55-79ea383ffb72. These are integration checks, not clinical or throughput evidence.

Use docs/DEPLOY_DR_TRAIN.md and docs/RELEASE_TRIADIC_DEPLOYMENT.md before updates. Private server.env, source backups and tunnel credential stay outside Git. The owner-requested test01 password is not in artifacts; its account is clinician/patient-001 only, no admin/finance/wildcard. Global account policy and existing users were unchanged.

The dated local/pause sections below are historical; their palette/setup-pending statements were superseded by this deployment. Latest evidence: evidence/triadic-release/public-final and evidence/deployment-20261113.

## Application

- Target checkout: C:/Users/User/Desktop/myProject/his-poc.
- Default app: backend.app.main:app, /api/v2, React apps/web, PostgreSQL 18.6 and Alembic.
- Windows Docker app remains available at http://127.0.0.1:8000/login.
- Use synthetic account registration or another seeded role; obtain its private password from local .env. No credential is included in this repository.
- Restart with python scripts/dev.py start; no automatic seed or reset. Data and backup volumes are retained.
- Source repository: https://github.com/siriponsri/his-poc. The user authorized pushing main; the later explicit named-host authorization covers the deployed POC above.

## Executed evidence

The Windows full run is evidence/fullsystem/windows-final/execution.json. It passed 69 original PostgreSQL tests and 13 additional auth/clinical/ERP tests. Two separate live-Uvicorn locking/security tests and 10 current legacy-import tests also passed. Frontend: 25 unit and 53 component tests; launcher/helper units: 19 plus 4 subtests.

Browser indexes:
- apps/web/evidence/fullsystem/windows-browser-execution.json
- apps/web/evidence/fullsystem/windows-browser-journeys-aggregate.json
- apps/web/evidence/fullsystem/windows-browser-extra-domains-aggregate.json
- apps/web/evidence/fullsystem/windows-recovery-final/browser-recovery.json

These retain source reports/hashes and actual IDs. The 10 journeys are composed from successful scenario runs, not an assertion that every earlier run passed. Initial failures are preserved.

The UI-created backup/restore was verified independently using read-only database connections: evidence/fullsystem/windows-20261113/browser-restore-verification.json. It checks 109 tables including Alembic, one file, two persisted file references, and eight exact UI-created records. The isolated restore target is his_restore_023ee48338444e91a116beab132b9e46; the active database was not overwritten.

## Repairs and invariants

Preserve shared identity/scope, immutable evidence/proposal versions, authorization rechecks, atomic domain audit/ledger/idempotency and fail-closed provider selection. Imaging file download now requires content/export rights and records a bounded audit event. Support-entity audit reads use the existing actor-visible list policy.

Security-denial logging runs in a worker thread. Do not put blocking database operations back into async HTTP middleware: a denial's user FK can wait on another request's identity transaction and otherwise freeze the event loop. The live locking regression demonstrates continued health responses and eventual persisted denial audit.

Contracts/data dictionary were exported from runtime definitions, including all 13 ERP create/action schemas. Hash manifests describe actual delivered bytes; .gitattributes prevents newline rewriting.

## Continue safely

Reproduce on a new isolated synthetic environment before changing code. Use a fresh validation output directory and inspect every exit code. Browser scenarios now use fresh encounter records where repeat runs require them; retained failures must not be erased to improve status.

No internal acceptance blocker remains in the reviewed local scope. Future external work requires named resources and session authorization. Hospital interfaces, production IdP, clinical deployment, payer certification and clinical/product evaluation remain NOT_RUN/UNKNOWN/NOT_CONNECTED as applicable. Baseline AI evidence is explicit DEMO mock; the named live document route below has actual inference evidence.

A repository-wide software license has not been selected. Third-party notices and generated-logo provenance are recorded separately.

## Real dr-train document route

Local private .env now opts into dr_train_ollama, while committed defaults remain mock_demo. Docker app on port8000 is running this explicit live synthetic profile. Existing SSH private-key configuration is used through a loopback-only forward; no key or endpoint identity is published. dev.py start verifies/starts that forward only when both live profile and tunnel opt-in are set. Read docs/DR_TRAIN_AI.md for native/Docker URL distinctions and pinned model/engine configuration. Migration0002 adds durable inference reservation/provenance without resetting data. A pre-migration backup is recorded under evidence/fullsystem/live-ai.

Actual Typhoon inference: three authored Thai cases PASS; browser document → task → five source-quoted checks → human edit v2 → approve → commit → reload PASS7, followed by read-only exact run-row PASS2. Sample run11.205s,408 input/141 output tokens,cost null. Evidence: apps/web/evidence/fullsystem/live-dr-train-final/browser-live-ai.json and live-dr-train-readback/browser-live-ai-readback.json. PostgreSQL17 orchestration tests use injected providers and are not extra real-model observations. Mock core18 and provider/tunnel/frontend regressions passed.

Never hold a database transaction across inference. Keep durable started/outcome rows, actor+key replay, one active inference across users/workers, absolute HTTP deadline, post-call permission/session/scope/source checks, and version-bound human approval. A client deadline closes transport; cancellation inside the remote engine is UNKNOWN. Exact quote checks do not prove semantic correctness. DR/CAD remain unconnected to live prediction. MedGemma is installed but not inference-tested. No model download, Cloudflare deployment or remote service restart was performed.

## Historical frontend refresh / Cloudflare pause handoff — 13 November 2026

The user superseded the green identity with yellow/gray/purple/orange using four supplied visual references and four inspected URLs. Incoming Claude working files were copied to ignored var/frontend-before-refresh before refinement. Preserve that backup; a local Vite design config remains ignored and is not the production deployment path.

Current app on8000 serves the rebuilt themed UI with the unchanged real dr_train_ollama backend profile. Frontend verification:25 unit/63 component plus audit/typecheck/build and runtime dependency audit PASS. Browser13 observations PASS on desktop1440 and mobile390, including persisted five-item live report and11205ms provenance; no new inference/domain mutation was performed. Runtime binding PASS45 files; readiness0002. Evidence: evidence/frontend-refresh/production-browser and final-themed. Initial stale greeting assertion failure remains under final-checks. Three reviewed accessibility/expansion defects were repaired and have regressions. Backend application code remains unchanged from dae61fc; new Cloudflare helper tests are separate.

The selected target is his.ai-cie.com. Read-only user-browser inspection confirmed ai-cie.com is present in the logged-in Cloudflare account with Full DNS setup and Active registrar status; no account state was changed and no private account IDs were saved in project artifacts. User said no Tunnel yet and requested manual setup instructions, then pause until they return.

Next: docs/CLOUDFLARE_SETUP_TH.md steps1–5. Private var/cloudflare/settings.json has hostname but still needs the owner's tunnelUUID/credential path/team/AUD. Do not ask for secrets in chat. New helper validates exact-host Access-required ingress, securecookie/HTTPS origin,90s transport deadline and private ports; local fixtures passed, actual account profile is not configured. Public DNS/tunnel/external workflow remain NOT_RUN. When owner resumes, inspect current files/state, validate private settings, retain backup and apply the HTTPS profile before starting a named connector; then execute external Access/login/scope/real-model/human-review acceptance. No implicit public publishing is claimed from this preparation.
