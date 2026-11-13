# Independent change review — browser transport and Docker build

Reviewed at: 2026-11-13T12:10:04.660868+00:00 (19:10 Asia/Bangkok).

Reviewer: delegated read-only reviewer, separate from the implementer of the changes below. Review scope is the default-fetch receiver fix, its regression, and the Docker frontend build dependencies. This review does not certify all domain or journey acceptance.

## Reviewed source snapshot

| File | SHA-256 |
|---|---|
| apps/web/src/lib/client.ts | `6992d938792223808e2d12929669a5e97ef053539c954eec037ee04523ff99ac` |
| apps/web/tests/client-v2.test.mjs | `b7c8f2e139f133778b825ed6c09d445d22104b61bec696b96e356b70e8abd44b` |
| Dockerfile | `277dcdcb079ae5bed93f7cdf474a250e9b84dbac5c0770bad134ac336b6ce143` |
| .dockerignore | `e5621f7c548afc30261ed3b423241a1d11c908c5122190c34ffa2226c7053742` |
| apps/web/scripts/sync_full_catalog.py | `61329380638ba812cae196bb8c0a31939a97a523212e0d788948e7908ea93e57` |

## Findings

No actionable correctness or security finding in the reviewed changes.

The `Client` constructor binds the default native fetch function to `globalThis`. Requests invoke `this.fetcher(...)`; keeping an unbound browser fetch in that field can supply the Client instance as its receiver and fail before making an HTTP request. Binding the default preserves the browser receiver. Explicitly injected fetch functions still use the supplied implementation. The request URL, same-origin credentials, CSRF header, idempotency key, response parsing, and error classification are unchanged.

The new regression replaces global fetch with a regular function that asserts its receiver is `globalThis`, creates the default Client, and performs a login-shaped mutation through the real request method. This exercises the receiver condition that an arrow-function mock would hide. The test restores the original global in `finally`. Its successful response assertion also ensures that a receiver assertion swallowed into `NETWORK_ERROR` cannot pass the test.

The Docker web stage now installs Python and the `python` command alias required by the package's build script. It also copies both backend catalog JSON files to the exact paths used by `sync_full_catalog.py`. The inspected script's remaining inputs are under the already copied `apps/web` tree. The production stage retains its non-root application user, PostgreSQL client dependency, and existing startup command. The ignore rules exclude local environments, credentials, databases, backups, and development storage from the build context. Synthetic tests, documentation, and evidence remain included by `COPY . .`; no sensitive-content issue was established in this scoped review.

## Verification observed

The reviewer independently executed this command from `apps/web`:

```text
rtk proxy node --import tsx --test tests/client-v2.test.mjs
```

Observed exit code: **0**. Result: **8 tests PASS**, including the new strict-receiver regression and existing CSRF/idempotency, error, mutation, reconciliation, routing, collection, and session checks. No tests failed or skipped.

The reviewer inspected, rather than reran, these integrator-produced artifacts:

| Artifact | Observed result |
|---|---|
| apps/web/evidence/fullsystem/windows-smoke-initial/browser-smoke.json | FAIL after one assertion; login UI showed `NETWORK_ERROR`. Client hash was `42c2e6d12fd1dc5290f411092bdddb9602c201092f5c0697a4d0ce723662dba7`. The artifact alone does not prove the native exception or absence of network requests; those were reported separately by the integrator. |
| apps/web/evidence/fullsystem/windows-smoke-fixed/browser-smoke.json | PASS, 11 browser assertions; includes login, PostgreSQL-backed patient creation, reload persistence, route denial, logout, portal shell, mobile navigation, and no uncaught page errors. Client hash matches the reviewed fixed snapshot. Scope is explicitly SMOKE_ONLY. |
| evidence/fullsystem/windows-20261113/frontend-fetch-fix/execution.json | Five checks have exit code 0: frontend unit, component, audit, TypeScript, and production build. Checks completed between 12:08:01 and 12:08:38 UTC on 2026-11-13. |
| evidence/fullsystem/windows-20261113/docker-start-fetch-fix.txt | Image build completed, app container recreated and started, and launcher reported the local login URL ready. |

Assessment: **READY_FOR_REVIEW for these changes**. The native browser symptom, targeted regression, rebuilt application, and executed browser smoke support the transport repair. Complete D01–D38 L2 and J01–J10 L3 acceptance remains outside this review; external integration, live inference, deployment, and clinical effectiveness are not established.

## Follow-up review — audit inspection, integer forms, and stock lookup

Source snapshot captured at 2026-11-13T12:15:43.810396+00:00 (19:15 Asia/Bangkok). This section extends the scoped review; it does not supersede the earlier source snapshot.

| File | SHA-256 |
|---|---|
| apps/web/src/App.tsx | `5a05a13773ca233373ba0cf290aae6de22c818b23ec8656904e5e53e67621912` |
| apps/web/src/components/forms.tsx | `d0b8cbb9369ba789217c284d2c44208a8e7e354271aa5f942d8e2982f5cf9a59` |
| apps/web/tests/workflow.component.test.tsx | `d4085f6946d54aa18c2ebcd8110f1ceaf8ee9ddb98f2d80331b6b7896511975b` |
| backend/app/domains/erp_catalog.json | `7ca5027559341ed4d5efe3c07e57f089002fa0898b0ef3b0c1c4b169bb2fe56e` |
| apps/web/scripts/sync_full_catalog.py | `4c5f13534388a30c023ddaddbcd61b2d91c7f69c6fd2cb9412f16d470af5584b` |
| backend/tests/test_catalog_encoding_unit.py | `c45c1d924f5f7477dee3d8cc982d89074df8ac450c92752fe7a1a223dd5457d1` |

No actionable finding in these follow-up changes.

The audit resource now sets `detailPath:false`, using the already authorized list record for inspection rather than requesting an unsupported audit detail endpoint. It has no create fields or mutation actions. The mounted App regression exercises the real `/audit` route, selects a list record, checks the displayed entity/action, and asserts no `audit/{id}` request. Backend authorization remains responsible for the list and history data.

Integer fields render as numeric inputs with step 1 and retain their minimum constraint. Submission converts only fields explicitly typed `integer`, checks `Number.isSafeInteger`, applies the minimum, and stops before the write callback on invalid input. D35 sequence is declared integer, required, minimum 1, matching the backend's strict integer DTO. Other numeric fields retain their string payloads, preserving Decimal money precision. The tests cover valid integer serialization, unchanged large Decimal text, fractions, an unsafe integer, and a value below the minimum.

Catalog synchronization maps `stock-locations` to `erp/options/stock-locations`. The inspected backend options route permits bounded consumers including D08 and returns rows scoped through the shared actor. The change corrects the lookup path without granting a new permission or creating an unscoped endpoint. The isolated catalog regression asserts the D08 dispense action's generated location source as well as D35 integer metadata under a simulated legacy Thai encoding environment.

Reviewer-executed checks:

| Command | Observed result |
|---|---|
| `rtk proxy node --import tsx --test tests/workflow.component.test.tsx` from apps/web | Exit 0; 52 component tests PASS, zero failures or skips |
| `rtk proxy .venv/Scripts/python -m pytest backend/tests/test_catalog_encoding_unit.py -q` from repository root | Exit 0; 1 test PASS |

The reviewer also inspected `evidence/fullsystem/windows-20261113/frontend-final/execution.json`: its frontend unit, component, audit, typecheck, build, and launcher checks all record exit code 0. Those checks completed before this review and do not by themselves establish execution of a subsequent catalog source snapshot. The independently executed catalog test above covers the reviewed mapping. Browser journeys and domain acceptance remain separately evidenced work; no complete L2/L3 claim is made here.

## Canonical acceptance gap audit — 2026-11-13T12:27:00.151150+00:00

This audit compared the canonical matrix and acceptance plan with the existing PostgreSQL tests, domain coverage test definitions, browser journey/domain/recovery scripts, and available execution artifacts. The reviewer subsequently authored the ERP additional tests below; their authorship is disclosed and they are not represented as an independent code review of those tests. Coverage files were not edited by this reviewer.

| Reviewed additional source | SHA-256 |
|---|---|
| tests/fullsystem/test_clinical_acceptance.py | `e23ca25e4723917d90c2ca7c34f475b7f60c91ba04bb63972099d6b268227228` |
| tests/fullsystem/test_erp_acceptance.py | `8bb2818fa1eb47b6f2a79105e24c7a88115cd0e667ae22309c1c4081d2791694` |
| tests/fullsystem/test_auth_acceptance.py | `15657de0e74822b89a5583dac7699bf6843eabfdf79893a95bb9cc6b4d0f0642` |
| apps/web/scripts/browser_journeys.py | `1324e5d1f19a79e1ef363dfc345fdef0968dd4b95b0353094f18dd5b7ab42856` |
| apps/web/scripts/browser_domains.py | `d9729515c844f62d538d9192a352f674f2fd1949cb9fbff16e18c59a7aeb2935` |
| apps/web/scripts/browser_recovery.py | `9f6611c48310fa53dd0f99225e25ffd5b51d667fd2d70c85bd715bcb0b23465a` |

The following previously identified canonical gaps now have executed PostgreSQL evidence:

| Domains or acceptance | Additional assertions | Observed log |
|---|---|---|
| D04, D05, D06, D11, D19 | Admission request replay creates one admission; transfer frees the previous bed with history intact; a distinct designated nurse acknowledges while another is denied; actual imaging-file GET denies unauthorized subjects/roles without bytes or success audit; cancelled diet cannot prepare or leave partial writes | clinical-additional.txt: 5 PASS |
| D23, D24, D28, D33 | Duplicate charge source and exact adjustment replay preserve original charge; duplicate remittance source across distinct claims causes no second write or approval; two-location stock transfer conserves lot quantities and replays once; every report lineage resolves to its source/version/status and original exported content remains unchanged after correction and changed source data | erp-additional.txt: 4 PASS, wrapper exit 0 independently observed by test author |
| AUTH-02, AUTH-03, AUTH-10 | Explicit HTTP/HTTPS cookie profiles, HttpOnly/SameSite/Secure attributes, mutation CSRF rejection without writes, old session rejection after logout, generic failed login and throttle at ten recorded attempts | auth-additional.txt: 3 PASS |

The first ERP additional run had 3 PASS and one overstrict test assertion: a different operation key reloaded the same charge with equivalent Decimal scale and timezone representation. That failure is preserved in `erp-additional-initial.txt`. The corrected test compares identity, exact source/version, Decimal values, the actual datetime instant, and database counts; same-key operation replay still requires exact response equality. The subsequent disposable PostgreSQL 18.6 run completed with all four tests passing. No backend edit was made to satisfy these tests.

Remaining local acceptance evidence at this audit snapshot:

1. Final browser execution is still in progress. Available final-retry journey evidence records J03 failure after J01/J02 pass; the separate D30 credential browser attempt records failure. Earlier passing scenario evidence remains valid for its own recorded source, but cannot certify later changed snapshots. J08–J10, the new other-subject portal assertion, recovery/restart/audit scenario, and the requested UI restore must receive their own executed results before a complete local acceptance claim.
2. The D30 canonical case requires credential denial **and its audit**. Existing tests prove the 403 and restored authorized behavior, while the denied-action SecurityEvent is provided by shared middleware. A test has not yet bound that specific denied actor/route/status to its persisted event. The generic core denial audit test does not establish this exact path.
3. D38 has actual PostgreSQL, API, and CLI isolated restore tests, including row/file fingerprints and tamper/missing-file failures. The browser journey currently proves backup completion only. The requested browser restore should verify the same app's UI-created record/file references against the restored inventory and hashes; a `restore_verified` label alone would not close that end-to-end evidence link.

No further local implementation defect was established by this scoped audit. These remaining items are evidence requirements, not a claim that unexercised behavior is defective. Live inference transaction behavior is separately NOT_RUN: no named live route/resources have been authorized or verified. Live providers, external interfaces, production/site operations, and clinical effectiveness do not become local acceptance failures merely because their external resources remain unavailable. No blanket L2/L3 certification is made by this report.

### D30 audit evidence closed — 2026-11-13T12:29:40.457017+00:00

The reviewer/test author added a focused D30 test in `tests/fullsystem/test_erp_acceptance.py` (updated SHA-256 `19335a7f3a102555c704f6b8688ef8b3aef6f4eb56291b074d354c0d9b3af060`). The following command was executed through `rtk proxy` with the venv Python, capturing output to `erp-credential-audit.txt`:

```text
python scripts/test_with_postgres.py --pg-bin C:/Users/User/.cache/his-poc-tools/pg18/pgsql/bin -- python -m pytest tests/fullsystem/test_erp_acceptance.py -q -k d30
```

Observed wrapper exit code: **0**. Disposable PostgreSQL 18.6 result: **1 PASS, 4 deselected**, 11.18 seconds. Deselection is explicit; this run does not recount the four previously executed ERP tests.

The test publishes a nurse roster, suspends that nurse's credential, and submits the denied acknowledgement through the authenticated API. It verifies exactly one new persisted SecurityEvent with actor `user-nurse`, organization/facility scope, POST method, the actual local route template `/erp/D30/records/{record_id}/actions`, status 403, and `request_denied_or_rejected`. It checks bounded metadata excludes credential/body/header columns, the password and submitted roster ID do not appear in event values, and the denied roster version/status remain unchanged. Explicit credential reactivation then permits acknowledgement. No backend changes were required.

The initial test expected the router prefix to appear in route metadata. It correctly observed the local included-router template instead. That failed assertion is retained in `erp-credential-audit-initial.txt`; the exact expected metadata was corrected before the passing rerun. Item 2 of the preceding timestamped local gap list is therefore closed. Final browser execution and the same-app UI backup/restore evidence remain separately tracked by the integrator.

## Security logging and support-record audit review — 2026-11-13T12:35:07.990324+00:00

| Reviewed file | SHA-256 |
|---|---|
| backend/app/main.py | `59e5f52ce6f80d1e9447a08baf99cca713d8f7e6c9ed3f2b4856319e37089518` |
| backend/app/core.py | `cdbf28f90cef7d833aafa09e9f36c1fbb3ef5b45528353ab166e4f466f115483` |
| backend/app/domains/erp.py | `08ff54c70134a9552b2a69e9523c456f4f55ec3de9b8ce03877d90a8c0d44653` |

The integrator reported a live Docker freeze in which a SecurityEvent foreign-key check waited on an identity update while synchronous middleware logging occupied the ASGI event loop. This review inspected the repair but did not independently capture that original database activity. The repair extracts synchronous SecurityEvent persistence into a separate function and awaits it through `run_in_threadpool`. That allows other ASGI work, including request teardown/transaction completion, to run while PostgreSQL logging waits. The separate short transaction, bounded event fields, identity lookup, denied HTTP statuses, and failure header remain equivalent. Domain write/audit/idempotency transactions are not moved or split by this change. A live-Uvicorn lock regression is being prepared separately; static inspection does not count as its execution result.

**Actionable finding (P2): apply staff visibility before granting staff audit access.** The newly added `erp.SUPPORT` branch in `core.audit_list` checks domain read permission and `erp.scoped` organization/facility scope. `erp.rows` imposes an additional StaffMember visibility rule: non-quality/hr/roster-manager/auditor/system-admin users see only the staff row linked to their own user. The new audit branch does not apply that rule. A nurse has D30.read and can therefore request another same-facility staff member's entity audit despite that staff member being excluded from the nurse's staff listing. Credential audit entries include reasons and actor history, so matching organization/facility alone is insufficient for this resource. This is a source-derived authorization regression; a direct runtime reproduction has not been executed by this reviewer at this snapshot.

Required correction: retain the support-record domain and organization/facility guards, add the existing staff-specific visibility boundary before audit access, and verify own staff plus authorized quality access succeed while another same-facility staff, cross-facility staff, and users without D30.read are denied. No backend file was edited by this reviewer. This finding was sent to the integrator before completion of the review.

### Staff audit boundary correction reviewed — 2026-11-13T12:35:41.189545+00:00

Updated `backend/app/core.py` SHA-256: `184bacda02d813c03f1c9a186177883567e499a700f6c75835822883322d726f`.

The integrator added a membership check against the existing `erp.rows(db,actor,model)` visibility policy after the support-domain permission and organization/facility scope checks. This reuses the staff listing's own-user restriction instead of introducing a second role policy. A target hidden by that policy now returns 404; quality users retain the authorized listing scope. The finding is corrected by source inspection. Runtime regression for authorized own/quality access, same-facility other-staff denial, cross-scope denial, and the live server lock scenario remains delegated to a separate test owner and must retain its executed result. No new actionable issue was identified in the narrow corrected branch.

### Live lock and staff visibility regressions reviewed — 2026-11-13T12:41:18.313775+00:00

The reviewer inspected `tests/fullsystem/test_security_event_concurrency.py` (SHA-256 `e586e45a4d901904a0a0f4db49960b170bf56446e3095f1d40581d6725cd780a`), the executed log `security-event-concurrency.txt`, and `security-event-concurrency-records.json` (SHA-256 `a6a73a6548377a02bfdfc9eed721e0f076a9e6585f10c89293a96508d55df06b`). Production source hashes remain main.py `59e5f52ce6f80d1e9447a08baf99cca713d8f7e6c9ed3f2b4856319e37089518` and core.py `184bacda02d813c03f1c9a186177883567e499a700f6c75835822883322d726f`.

Observed executed result from the separate test owner: **2 PASS**, 63.89 seconds, actual disposable PostgreSQL 18.6 and a real loopback Uvicorn subprocess. This reviewer inspected the results and test implementation; the execution is not claimed as a second reviewer-run repetition.

The concurrency test meaningfully creates the failure condition: a separate PostgreSQL connection holds `FOR UPDATE` on user-quality while an authenticated forbidden request reaches a SecurityEvent INSERT. A second connection observes a real database Lock wait in `pg_stat_activity`; the test also asserts the denied HTTP request is still pending. It then requires an independent real HTTP `/health` request to complete before releasing that lock. Recorded result: HTTP 200 in 1.047 seconds, followed by the original 403 and a persisted scoped SecurityEvent (`7f686986-5495-40ac-ab79-f2818981949b`). This exercises ASGI liveness during a blocked FK check rather than relying on an ordinary TestClient request or a mocked delay.

Cleanup is bounded: the held transaction rolls back in `finally` before the pending future is joined; connections and the executor are context-managed; the fixture terminates Uvicorn and escalates to kill after a timeout even on failure. Clients are closed in test cleanup. The server and database targets are constrained to loopback and an explicit disposable PostgreSQL test URL. No application database reset or external service is involved.

The staff audit regression verifies quality access with a real credential audit row, wrong-role 403, other-facility 404, nurse-own 200, nurse-other-staff 404, and quality-other-staff 200. Denied responses are checked for absence of the credential event. The results support closure of the scoped staff-audit finding and the event-loop liveness repair. No new actionable finding was identified. This closure does not certify browser D38 restore, remaining journey execution, or full-system acceptance.

## Final local acceptance recommendation — 2026-11-13T12:49:15.004556+00:00

Recommendation: **accept D01–D38 at local synthetic L2 and J01–J10 at local synthetic L3**, using the combined PostgreSQL, browser, concurrency, recovery, and restore evidence. No remaining local must-have blocker was identified in this scoped acceptance audit. The integrator must reconcile coverage/release documents and preserve the reviewed source and evidence in the final package. This recommendation is for the implemented local minimum workflows, not every possible domain feature, every device/viewport combination, production operation, clinical effectiveness, or L4 integration.

| Final artifact inspected | SHA-256 |
|---|---|
| apps/web/evidence/fullsystem/windows-browser-journeys-aggregate.json | `698923a98fd2533c92bed966bc6d98ecd2bfb01456debabcf7345685eab492b2` |
| apps/web/evidence/fullsystem/windows-browser-extra-domains-aggregate.json | `a2faaf59b4717a48b5cbd4b5a12284fd102891223b043d06e64fddf41279286b` |
| apps/web/evidence/fullsystem/windows-recovery-final/browser-recovery.json | `37e3f7eab7018e73d6d87ca7b2c91d7b832eeaa088fb726d31a293e3f194be70` |
| evidence/fullsystem/windows-20261113/browser-restore-verification.json | `501db4ac6f267de39c33debb65f2c454be30c1950f26ca552c7dff4df177268e` |
| evidence/fullsystem/windows-20261113/final-runtime-binding.json | `c39751e23e69ce9acc3e702e962375a9c18de3d96b9255d8ca9ec3a9c191c48d` |

The reviewer independently checked that all ten aggregate journey entries and all twelve extra-domain entries exactly match their referenced executed source entries, that every source report hash matches its file, and that every selected entry is PASS. This is a composition of recorded runs, not a claim that all scenarios ran in one final invocation. Earlier failed attempts remain retained. The extra-domain aggregate includes executed persistence/history/role-denial checks for domains outside the ten main journeys and the separately rerun D30 credential path. The final smoke report also records 11 PASS assertions. J10's selected source records another portal subject's request and the actual denied read (404), with the private reason absent from the authorized subject's screen.

The final recovery report records **9 PASS assertions**: real stale-action 409, definitive recovery, audit display, cookie/storage checks, direct forbidden API access, delayed cross-patient response protection, non-seeding app restart persistence, and rendered backup followed by rendered isolated restore. The restore action is observed through actual UI controls and an operations response, with a restore job bound to its selected backup and the four declared verification checks.

The independent read-only restore verifier goes beyond trusting the UI status. Its inspected implementation connects to the source and named `his_restore_...` target in read-only repeatable-read transactions, rejects the active database as the target, compares restored table/file inventories against the backup manifest, validates file references and foreign-key state, and checks fixed-map browser record IDs. The executed report verifies **109 total tables, one stored file, two persisted file references, eight exact browser-created rows, and the imaging file SHA-256**. Those rows include J01 patient/encounter/document/result, J05 invoice/receipt, and J08 imaging/document records. The verifier's bound journey-report hash exactly matches the reviewed aggregate. This closes the earlier missing link between UI-created data and actual restored data.

The reviewer also independently compared every listed final runtime-binding hash to the current local file: all **27 backend/build files match**, with no mismatch. The running-source binding and targeted tests cover the later main.py/core.py fixes; prior unaffected browser scenarios retain their own source snapshots. `final-fixes/execution.json` records zero exits for frontend unit/component/audit, typecheck, build, clinical, and launcher checks. These results complement the previously reviewed canonical clinical/ERP/auth additions and live lock regression; none is substituted for another evidence category.

Accordingly, the three timestamped remaining-local-evidence items above are closed: final rendered scenario execution, D30 denied-action audit, and same-app UI backup/isolated restore with independently verified data and file contents. Live inference transaction behavior remains explicitly NOT_RUN under the unavailable/unauthorized external route, and live model identities, endpoint revisions, external-system certification, clinical validation, and production readiness remain outside this acceptance. No clinical or L4 success is recommended or implied.
