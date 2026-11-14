# CareBalance integration validation checkpoint

Latest DR software/image qualification and remaining Linux/public gates:
[DR_RELEASE_20261114.md](DR_RELEASE_20261114.md). The owner explicitly holds the
ten renamed MMRDR images pending laterality; tests use authored fixtures.
Existing public LabClear remains unchanged while the new DR shadow is rehearsed.

The long goal remains ACTIVE. This checkpoint distinguishes the qualified
LabClear connector from ongoing DR receiver work. Synthetic software validation
does not establish clinical effectiveness or authorize real-source transfer.

## LabClear

The HIS gateway is implemented with three additive PostgreSQL evidence tables,
explicit scoped import/read/confirm/recovery, current session and task checks,
CSRF, immutable released laboratory source and durable unknown-outcome recovery.
The receiver is a source-only19-file package from the authorized LabClear
checkout, with a separate database, key, encrypted state and service identity.
It does not expose the existing LabClear customer/staff/OCR/model application.
Startup rejects an incorrect or unprepared database before routes are registered.
The existing LabClear deployment and owner work remain outside deployment scope.

| Verification | Actual result | Evidence |
| --- | --- | --- |
| Independent HIS regression | 14 PostgreSQL18.6 suites/cases passed, including backup/isolated restore and Alembic drift check | [execution](../../evidence/integrations/independent-gateway-review-20261114/results/execution.json) |
| Independent gateway negatives | 44 targeted tests with62 subtests passed | [XML](../../evidence/integrations/independent-gateway-review-20261114/results/gateway-independent.xml) |
| Packaged receiver startup guard | Two actual PostgreSQL tests passed: wrong database/unprepared startup denied, prepared two-DB exchange | [XML](../../evidence/carebalance-gateway-20261114/packaged-startup-guard.xml) |
| Final HIS frontend | 25 unit,117 component,3 audit cases, typecheck/build passed; two new mounted regressions | [receipt](../../evidence/integrations/labclear-final-ui-20261114/checks.json) |
| Private deployed HTTP/PostgreSQL |14 checks passed: released42 to reviewed43, confirmation/readback/retry; actor/session/patient/CSRF denial; no automatic HIS task completion | [shadow receipts](../../evidence/integrations/shadow-validation-20261114/README.md) |
| Actual private browser | Import42, explicit edit43, same-person confirmation, persisted reopen43 disabled; source42 unchanged;390px layout/inert/Escape/focus restoration | [browser receipt](../../evidence/integrations/shadow-browser-20261114/acceptance.json) |
| Fresh-login defect and repair | Initial query loss retained as FAIL; final5328 candidate preserves patient/encounter/record after real fresh login | [repair proof](../../evidence/integrations/shadow-browser-20261114/fresh-login-fixed.json) |
| Candidate source binding | Final5328 image verifies231 source files and17 built assets | [binding](../../evidence/integrations/deployment-labclear-20261114/built-image-source-binding.json) |
| Schema-compatible rollback | Actual old-UI compatibility image tested against same0003 shadow database; final candidate restored | [recovery](RECOVERY_0003.md) |
| Public activation | PASS: final5328/receiverc194 ready,112 tables;109 legacy counts/181 sessions/three results/file/account preserved; actual backup restored separately | [operations](../../evidence/integrations/deployment-labclear-20261114/ops-activation-runbook.md) |
| Public connector browser journey | PASS: owner-verified Access, test01, explicit review task/import, source6 to reviewed7, same-person confirmation, reload/read-only reopen;390px layout; zero model calls | [public browser](../../evidence/integrations/public-labclear-20261114/acceptance.json) |
| Public persisted readback | PASS:9 HIS,8 receiver and6 preservation checks; one import/confirm/read, source6/v10 unchanged, reviewed7/revision1, task open, inference9 to9 | [database proof](../../evidence/integrations/public-labclear-20261114/public-readback-database.json) |

Final candidate is `his-poc-server:workspace-5328d8216f0f`, image SHA256
`a57b43d918bbbfe05cc444c1273ae952a46407efef017631bbd15f8c7b5b4ee6`.
Receiver image is `his-poc-labclear:source-c1944c772e87`, SHA256
`d02a78be86e67d8fc64f5133ceb5a07ab2270b4e97ad44f4fa518748da539b6f`.
There were zero new model calls during these connector tests.

Active public HIS and receiver images match the final candidates above. A fresh
predeployment dump was actually restored to a new isolated verification DB with
all109 table counts matching. Only the HIS app was replaced; existing DB and
Cloudflare connector IDs remained unchanged. Future operations must layer
`server.env` then `labclear.env` and the base plus receiver overlay; base-only
startup selects the old image and is unsuitable after migration0003. See the
operations runbook. No production seed or restore occurred.

Private shadow databases share a validation-only PostgreSQL cluster/admin role;
that is not proof of production role isolation. Production uses a distinct
dedicated receiver database/role and private loopback listeners. The original
HIS database, connector, Access/DNS and document-AI model are preserved.

## DR derivative

Independent checkout: `C:/Users/User/Desktop/myProject/carebalance-dr-screening`.
Original baseline source revision: `6ae2952b740165c9becc06964dddc93069a82028`.
Derivative theme main: `eacdef0bf55f0cae493af632f147efc3a939e714`; documentation-only
main validation commit: `a9932be0094e6279c1c918de0c17cde217634421`.
Current receiver implementation branch: `feat/carebalance-his-bridge`.
No publication remote is configured, and no derivative push is claimed.

Theme branch validation passed458 tests, typecheck and build. Main validation
passed five focused files/32 tests, typecheck and build, with identical116 runtime
source hashes and nine output hashes. A single test checkout CRLF difference is
explicitly recorded, not represented as raw178-file equality. Actual empty-state
visual preview passed320/390/768px layout and mobile drawer checks. That preview
used authored API doubles and establishes no clinical auth or inference result.

The receiver contract now freezes one immutable patient/visit/task/source-set
workspace, current verified HIS actor, explicit signing capability, exact PNG
bytes/geometry, durable command recovery, no self-declared signer fallback and
manual-only clinical route allowlisting. Receiver implementation and its real
PostgreSQL/manual clinical round trip, HIS BFF, bound frontend and public journey
remain ACTIVE work. No original DR service or source is an integration target.

## Existing HIS document AI

The selected public real-AI result remains historical89-phase evidence. Final91
public saved-proposal reopening was later verified in authenticated Chrome, with
matching version2/hash/checklist and disabled mutations, zero new inference.
[Saved-result proof](../../evidence/research-ui-release/final91-public-reopen/acceptance.json).
Do not promote those results into DR or LabClear clinical/model acceptance.
