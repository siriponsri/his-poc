# CareBalance integration validation checkpoint

## Latest realistic-patient checkpoint

The long goal is ACTIVE. The production fictional cohort/API batch PASSED: 146 normal mutations once; six new patients/OPD visits/notes, eleven released labs, twelve OPEN reviews (23 total new tasks includes eleven completed acquisition tasks). Four legacy Patient display names changed with audited version1→2; old DOB/sex/HN and every old nonpatient row/file remain. All9 prior inference runs/results remain; DR/LabClear rows and credentials/roles are unchanged.

The independently reviewed UI source5a26ed6 is integrated into main: actual scoped identifiers, completed age, sex and readable visit context. PASS31 unit/139 mounted, typecheck/build; six PostgreSQL privacy cases and an overlapping nine-case scoped regression. The initial outdated Home fixture failure is retained. The live app is still HISa30 on migration04: this new UI is NOT_YET_DEPLOYED at this source checkpoint.

Pending: fresh current04 backup/isolated restore, candidate/rollback qualification, app-only activation, final authenticated rendered UI/DR label and retained workflow checks, then final publication/handoff. Current protected browser displayed all six new names and twelve review tasks on the prior app; this does not establish the new age/HN UI acceptance.

[Authored cohort and evidence](../../evidence/integrations/realistic-demo-data-20261114/DEMO_DATA.md). Earlier sections below are retained checkpoints with their original states and preservation scope; their NOT_IMPLEMENTED data status predates this completed batch.

## Earlier DR checkpoint at 12:04 UTC

The long goal remains ACTIVE. Public HISa30f is ready on migration04, dedicated
DR289/schema1 is ready and LabClearc194 remains ready. Three separate databases
and private loopback listeners retain their service identities. Fresh production
backup/actual isolated restore passed112 tables/one file at11:07Z. Activation
preserved original non-app containers/configuration, all112 legacy table row
hashes/files/sessions, all9 committed results/3 selected result hashes and
inference9. No production seed/reset/restore occurred.

The actual protected native-Chrome DR manual journey passed on the7c76 bundle:
explicit source consent, both authored640x480 originals, left manual quality
acceptance, checked patient/eye confirmation, unsigned draft save/full reload,
then an explicit unsigned review check; signing remained disabled. Separate
read-only PostgreSQL proof confirms left revision3/PRELIMINARY, exact notes,
verified-session quality/confirmation, one UNAVAILABLE read receipt, original
D11v6 source bytes, review task OPEN, acquisition tasks complete and grants0.
The original document-AI inference count remains9, without a new model call.

Final human-label frontend34fd static v2 refresh/preservation PASSED at12:04:20Z:
all3 databases/files and59 non-app container IDs unchanged, registry bytes/
UID10001/mode0600 preserved and10 authenticated assets matched. The initial
directory-preparation failure before dispatch is retained/reconciled separately.
Final label-only public rendered smoke is NOT_RUN after the physical Escape
browser stop, before the new-bundle reload. Do not equate earlier
7c76 browser PASS with the new bundle's rendered acceptance or close the goal:
the owner-added six-patient realistic fictional Thai/coherent clinical dataset,
metadata and UI task remains NOT_IMPLEMENTED, with explicit audited demographic-row exceptions required
after this preservation checkpoint. [Ten public-safe receipts](../../evidence/integrations/public-dr-20261114/receipts.json)
include the actual public draft [database readback](../../evidence/integrations/public-dr-20261114/public-browser-readback-20261114T115240Z.json).
See [DR release](DR_RELEASE_20261114.md), [browser checkpoint](DR_BROWSER_CHECKPOINT_20261114.md)
and [exact continuation](../../CODEX_HANDOFF.md).

Current source: HIS mainac63879 was pushed; derivative local maind8a2d9b has no
remote and preserves191 inherited backend files. Final DR qualification records
522 unique-case composite coverage:521 full-run passes/one retained native30s
timeout, unchanged isolated2-pass rerun; main76 focused/UWF2/typecheck/build pass.
HIS main77/receiver37 PostgreSQL, independent2 quality checks and HIS25unit/
135component/3audit/build pass. These are synthetic software/integration results,
not model or clinical effectiveness. Contracts04 are separately exported at
[contracts-0004](contracts-0004/manifest.json):142 paths/120 modeled/121 operational
tables. Baseline contracts/v2 retain their historical binding.

Ten owner-renamed MMRDR images remain HELD_FOR_LATERALITY, unchanged and unpaired.
No assignment, clinical registration, transfer or model call was made. Their
source attestation does not provide missing eye labels.

## LabClear source/theme adaptation

The authorized sibling LabClear theme work passed76 tests:16 theme/route/cache/
contrast tests plus60 existing business regressions. Bounded actual browser
checks were performed separately by the coordinator, including mobile actual
width355/requested390. All18 preexisting owner-modified file hashes remained
unchanged. Evidence remains in the sibling checkout at
`C:/Users/User/Desktop/myProject/LabClear/docs/evidence/carebalance-theme-20261114`.
Its existing Render deployment, OCR/model services and unrelated owner changes
were not deployed or repurposed by the dedicated HIS receiver.

## Historical LabClear qualification and activation

The LabClear records below retain their original candidate5328/migration03
phase. HIS is now on the04 image described above; the receiverc194, reviewed
laboratory value and original released source remain preserved.

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
