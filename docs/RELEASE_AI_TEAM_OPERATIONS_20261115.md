# AI evidence, accountable work and operations monitoring

Status: DEPLOYED_ACCEPTANCE_IN_PROGRESS. This report separates implementation,
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
| Mounted frontend | PASS, 223 cases and 31 units | Existing behavioral/accessibility checks |
| Guide content/media | PASS | 16 chapters, 101 steps, 38 domains/152 domain steps, 11 JPEGs, 10 walkthroughs |
| Copy follow-up | PASS, 7 existing source-evidence checks and typecheck/build | Wording only, exact marks/no cached fallback retained |

Initial failed fixture/harness executions remain in private working evidence.
They were not relabeled PASS: immutable-row test fixtures, combined-suite
admission pollution, an unseeded isolated core database and old expected UI copy
were corrected before the separately recorded successful executions. Two DR
checks skipped in an earlier environment were subsequently executed in the
correct isolated derivative environment. The retained Vite chunk-size warning
and Starlette/httpx deprecation warning were not hidden by dependency changes.

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

Copy-only source `d8755d9` has passed local checks and remains NOT_DEPLOYED at
this checkpoint. It clarifies that freshness reflects the whole preparation
context and that text-null snapshots can contain structured field evidence.

## Bounded model and browser acceptance

IN_PROGRESS. The frozen trial allows six initial application cases and at most
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

Native B1/B2 fixtures were created through normal web forms in separate new
encounters for the existing synthetic patient. Team queue claim, schedule,
eligible handoff and escalation were read back from the server on the same task.
The physical task version became 7 while its AI semantic version remained 1;
source digest and inference input hash remained equal after all coordination.
The initial native datetime automation fills did not fire the application change
event; those null-date results were retained. Real keyboard input subsequently
persisted a past date and enabled the overdue escalation check.

Cloudflare Access expired before final mobile/reload, native AI and Admin reads.
Those checks remain NOT_RUN pending normal user verification. Security settings
were not weakened and no service restart was used to address the Access expiry.
Final trial totals, native results, preservation audit and publication will be
recorded here only after execution.
