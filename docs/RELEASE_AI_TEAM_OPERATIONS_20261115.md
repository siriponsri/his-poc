# AI evidence, accountable work and operations monitoring

Status: DEPLOYED_ACCEPTED_AND_PUBLISHED. This report separates implementation,
local qualification, deployment and application acceptance. It does not extend
the historical 38-domain/10-journey baseline or establish clinical effectiveness.

## Delivered behavior

- Preparation selects profile-relevant exact passages before demographics and
  discloses partial and omitted sources. Permitted immutable source snapshots
  retain revision/hash and original Unicode code-point citation positions.
  Draft prose remains subject to human review; exact citations and typed fields
  are technical checks, not a clinical accuracy score.
- Team queue reuses the existing task identity, with eligible ownership/handoff,
  due date, operational priority and same-task overdue escalation. Domain
  completion and signing remain in their original workflows. Coordination-only
  changes preserve the semantic AI/legacy/LabClear/DR source version.
- Admin AI operations reads scalar metadata, counts, filters, usage, cost and
  elapsed time without patient charts, source bodies or host/model controls.
  Heartbeat and current model health remain explicitly unobserved; unmeasured
  cost remains null. Declared model configuration is not live qualification.

See the [task manual](AI_TEAM_OPERATIONS.md) and
[feature contract](AI_TEAM_OPERATIONS_CONTRACT.md).

## Local qualification

These checks used disposable PostgreSQL18.6 where applicable. Provider doubles
and isolated HTTP receivers are distinguished from production inference.

| Scope | Result | Evidence boundary |
|---|---|---|
| Assistant/provider regression | PASS, 169 checks | PostgreSQL-backed suites and offline provider doubles; no live model claim |
| New source quality/Admin checks | PASS, 8 PG + 9 pure checks | Exact excerpts, original offsets, scope, scalar projection |
| Admin regression | PASS, 35 PG checks | Existing account/session/permission behavior |
| Core journeys regression | PASS, 18 PG checks | Explicit seed in an isolated target |
| Team queue | PASS, 33 PG checks | Claim concurrency, current eligibility/revocation, idempotency and semantic identity |
| Legacy AI/LabClear/DR coordination | PASS, 17 PG checks | Coordination during existing review/connector boundaries, no duplicate effects |
| LabClear compatibility | PASS, 44 tests + 62 subtests | Controlled doubles/isolated database; no production model call |
| DR receiver interoperability | PASS, 2 HTTP scenarios | Isolated loopback derivative and authored PNG/JPEG; no DR model call |
| Mounted frontend | PASS, final 227 cases, zero skipped; retained 31 units | Final component suite ran with concurrency1 on b860 |
| Guide content/media | PASS | 16 chapters, 101 steps, 38 domains/152 domain steps, 11 JPEGs, 10 walkthroughs |
| Copy follow-up | PASS, 7 existing source-evidence checks and typecheck/build | Wording only, exact marks/no cached fallback retained |

Initial failed fixture/harness executions remain in private working evidence.
They were not relabeled PASS: immutable-row test fixtures, combined-suite
admission pollution, an unseeded isolated core database and old expected UI copy
were corrected before the separately recorded successful executions. Two DR
checks skipped in an earlier environment were subsequently executed in the
correct isolated derivative environment. The retained Vite chunk-size warning
and Starlette/httpx deprecation warning were not hidden by dependency changes.
The final default-parallel frontend run terminated one Node process with an
allocation failure after221 checks passed. That execution remains FAIL. Running
all14 component files with concurrency1 completed227 checks with no skipped
tests; no heap limit, application code or test selection changed for that run.

## Deployment checkpoint

The dedicated dr-train app serves [his.ai-cie.com](https://his.ai-cie.com) behind
the existing Cloudflare Tunnel and Access policy. App source
`1960a827ac96784de5b39d8c84e688c721e963cb` uses immutable image
`sha256:dfaad73737f8f318c87427a210a964d997076c639a25c5ad169935e3c5e1f3ad`
and schema `0006_team_coordination`. The server directory is a runtime snapshot,
not a Git checkout. Publication and deployment are separate operations.

PASS: fresh backups, explicit additive 0005-to-0006 migration, old 126-table
content preservation except the Alembic version row, empty new coordination
table, three database/file preservation checks, app-only activation and fresh
guard/engine/ENV verification. A compatible schema0006 fallback image was
qualified in isolation. No production database downgrade was attempted. Restore
of the exact fresh production backup and reboot recovery remain NOT_RUN.

The existing Typhoon/Ollama model, GPU0 route, context/output limits and worker
ENV remain unchanged. The deployment operator issued zero model generations.
The original six assistant runs and their eight revisions, five decisions,
seven effects and paused watch were preserved at this checkpoint.

Frontend source `b860725` was subsequently deployed as immutable image
`sha256:fcdbb821331d8433f26c754455a5fc184c6e5cd795de082990e1295abfd8398b`,
after all four handover phases passed. Its32 assets and four frontend
files add precise freshness/structured-evidence wording, queue focus after the
final asynchronous layout, visible Admin metadata selection and positioned
table containment for the visually hidden header. Sixty backend, migration and
dependency inputs and the inherited image Config remain byte-identical to the
original deployed base. Stage/build/static qualification and handover preserved all127-table, files
and trial-bundle hashes across the HIS/LabClear/DR baseline. This overlay retains
backend1960 plus frontendb860 identity; it is not a replacement backend release.

## Bounded model and browser acceptance

PASS for the six-case application cohort and final protected native smoke.
The frozen trial allows six initial application cases and at most
two separately reviewed corrective reserves, with no automatic retry, batch,
watch or direct provider call. Every reserved or unknown attempt remains charged.
API cases use normal production application authorization via in-process HTTPS
TestClient; they are not protected-browser wire tests. Native browser cases use
the public protected URL and remain separately identified.

All four API cases passed execution, source checks, root meaning review and
selected-effect replay. The [public API evidence](../evidence/ai-team-20261115/api-acceptance.json)
contains exact typed-field comparisons, bounded authored source passages and
the generated drafts so the substantive results can be assessed directly.

| Case | What was checked | Selected sources | Provider time | Prompt/output tokens |
|---|---|---|---|---|
| A1 Visit | Late history/pending passage in a long note; faithful draft | 8/17, one partial, nine omitted | 54,146 ms | 676/290 |
| A2 Nursing | One-person walking assistance/call bell; no laboratory control | 5/5 | 58,032 ms | 518/245 |
| A3 Records | Named consent/referral metadata and reception task; no clinical body or draft | 5/5 | 49,530 ms | 427/135 |
| A4 Laboratory | Both analyte/value/unit/range pairs selected and reported correctly | 7/7 | 48,576 ms | 531/98 |

Each case produced two exact typed-field facts and zero literal quote facts.
A1/A2 generated faithful narrative drafts that required human review; those API
drafts were not saved as D22 documents. A3 correctly left unknown demographic
metadata for review. A4 reported both ALT and glucose associations without
interpreting their ranges. No clinical accuracy or staff-time saving is inferred.

All four selected effects reused their existing authored fixture tasks without
creating duplicates. Same-key replay created no new run or effect. Measured cost
remained null. Four of eight generation slots were used, with no unknown dispatch
and no corrective reserve consumed. Two A2 outer pre-enqueue checks stopped on
an ordinary worker scan before reservation/API/model dispatch; both NOT_RUN
attempts remain retained. The existing dispatch lock then serialized one enqueue
against natural scan completion without a restart or configuration change.

After the API cohort, every original assistant row hash remained unchanged:
6 runs/8 revisions/5 decisions/7 effects/1 paused watch. Counts including the new
cases were 10/12/9/11/1. The nine legacy inference rows and nine committed-result
rows were also unchanged. No active run or watch remained at this checkpoint.

The two native protected-browser cases subsequently passed preparation, original
snapshot reading, human meaning review, selected unsigned-draft save and reload.
B1 preserved the authored Thai history/pending text, and B2 preserved the walking
assistance/call-bell handover. Each saved exactly one version1 unpublished D22
draft with no clinical attestation or extra task effect. Their recorded provider
times were53,391 ms and54,236 ms; usage was489/261 and489/265 prompt/output tokens.
The [six-case application evidence](../evidence/ai-team-20261115/application-acceptance.json)
keeps the actual native observations separate from private read-only server
corroboration and includes exact source/draft comparisons and saved-text hashes.

The final trial ledger records6 of8 slots, six positive provider dispatches,
zero unknown attempts and zero corrective reserves. All original assistant and
legacy row hashes remain unchanged; current assistant counts are12 runs,
14 revisions,11 decisions,13 effects and1 paused watch. No active run/watch
remains. The six examples generated12 typed-field facts and zero literal quote
facts. B1's original161 Unicode code points/162 UTF-16 units survived the native
round trip, but native quoted-offset highlighting was not exercised. Exact quote
offset behavior is covered by the separate local component/PG checks.

Native B1/B2 fixtures were created through normal web forms in separate new
encounters for the existing synthetic patient. Team queue claim, schedule,
eligible handoff and escalation were read back from the server on the same task.
The physical task version became 7 while its AI semantic version remained 1;
source digest and inference input hash remained equal after all coordination.
The initial native datetime automation fills did not fire the application change
event; those null-date results were retained. Real keyboard input subsequently
persisted a past date and enabled the overdue escalation check.

Cloudflare Access expired during the initial browser checks and was renewed by
the user through the normal sign-in flow. The resumed queue read retained its
owner, due date, priority and escalation. Admin normal sign-in,12-row metadata
view, nursing filter4, empty-state filter0, null cost and explicitly unobserved
heartbeat/model health passed. Patient names and the B1 clinical body were absent
from its metadata panel. No security policy was weakened.

Native reading revealed three frontend defects before final activation: a queue
deep link scrolled before its23-row layout finished; Admin details appeared below
the viewport; and an absolute1px screen-reader header escaped its unpositioned
table scroller, matching document width477 versus client380 at a390px viewport.
The deployed repairs passed final native checks. At a390px requested viewport,
Admin document width and scroll width were both380px; its table retained local
horizontal scrolling (348px client,541px content). Selected metadata headings
received focus and appeared at307.9px on mobile and299.4px on desktop. Queue
deep-link reload waited for the23-row layout, then focused the selected heading
at235.8px on desktop and197.95px on mobile. Both root layouts had equal client
and scroll widths. The same task retained version7, its clinician owner, due
date, high priority and escalation1. The used B1 source snapshot retained its
full original text, hash and structured status mark under the clarified copy.

See [final native evidence](../evidence/ai-team-20261115/browser-acceptance.json)
for exact observations and unedited returned screenshots. Temporary viewport
overrides were reset. No further model or clinical mutation was issued during
this final smoke.

## Final preservation and publication

The separately reviewed read-only audit passed at07:42:40 UTC. All original
business-row hash multisets were retained, with the documented0005-to-0006
schema transition and authored trial additions. All business rows present before
the final frontend overlay remained exact. LabClear's two tables, DR's ten
tables, three stored source files and the48-file trial bundle were unchanged.
The current image, guard, model/GPU identity, backend60/frontend4 inputs and all32
assets returned over HTTP matched the qualified release.

Normal final sign-in/logout added two audit events, one login attempt and one
session. An existing session changed only from a null to a non-null revocation
time; all its other columns remained exact. The audit separately checked the
original pretrial session change. No preservation audit wrote database records,
requested inference, restored a backup or changed services. The original
assistant and legacy histories remained intact, and the trial allowance stayed
at6/8 with zero unknowns and zero corrective reserves.

The first final-audit execution remains NOT_PASS: its expected asset map still
named predecessor files. An offline comparison identified that harness error;
the separately reviewed v2 changed only the32 expected asset hashes to the
qualified final build and then passed. This correction did not change deployed
application bytes or hide the failed receipt. See the
[public preservation receipt](../evidence/ai-team-20261115/deployment-preservation.json)
and [scoped local checks](../evidence/ai-team-20261115/local-qualification.json).

Fresh-backup restore, recovery after host reboot and fallback activation remain
NOT_RUN. Their preparations are not recovery acceptance.

The accepted release was published by non-force push to `origin/main` as
[`c856dbc585ec413ae212a8ef29bf27e117a18c8d`](https://github.com/siriponsri/his-poc/commit/c856dbc585ec413ae212a8ef29bf27e117a18c8d),
and the remote ref was read back at that exact commit. The documentation closeout
follows as a descendant; it does not redeploy the runtime. Private operator
receipts, credentials, database contents and source ZIPs remain outside Git.
