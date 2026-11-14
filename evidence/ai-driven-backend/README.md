# Assistant backend foundation evidence

Status: **OFFLINE BACKEND PASS; RELEASE NOT QUALIFIED**.

The candidate adds the four frozen preparation profiles, five additive tables,
scoped APIs, durable worker/watch polling, shared legacy/assistant admission,
and atomic reviewed document-draft/task effects. Existing source, inference,
proposal and committed-result tables are preserved.

Executed on an isolated, loopback-only PostgreSQL 18.6 database named `his_test`:

- Alembic migration to `0005_assistant_workspaces`: PASS.
- Alembic schema drift check: PASS, no new upgrade operations.
- Full baseline: 126 tests PASS, zero failures: 51 assistant, 5 provider integration,
  20 assistant-provider, 18 existing core, 32 existing document-provider tests.
  See `pytest-results.xml` for individual cases.
- After the final lease-clock repair: 17 targeted worker, admission, concurrent,
  timeout, legacy, authorization, terminal-visit and feature-flag tests PASS
  (37 unrelated assistant cases deselected). This includes three new clock-order
  regressions. The full baseline was not repeated after that narrowly scoped
  clock change. `lease-fence-execution.json` pins the final source hashes and
  `lease-fence-pytest.xml` names the executed cases.
- Existing document review and provider tests are included in that total.
- Full canonical compact inference view is bounded to 2000 UTF-8 bytes. Notes
  are included whole or explicitly omitted; all eligible source evidence remains
  in the server-side manifest and freshness digest. At most 12 sources enter
  the compact view, matching the frozen draft/effect reference cardinality.
- Four actual PostgreSQL role packets pass the actual provider/schema adapter
  through an explicitly offline HTTP MockTransport and durable worker. Complete
  input sizes including system/profile text are 1499, 1379, 1223 and 1250 UTF-8
  bytes for visit, nursing, records and laboratory respectively, each within the
  4096 budget after the 256 template reserve and 1024 output allowance. Exact
  details are in `provider-integration.json`; no live network/model call occurred.

`execution.json` records commands, exit codes, timestamps and exact backend
source hashes. `executed-core-journeys.json` contains this run's existing-domain
regression trace. The repository's historical core trace was restored after
copying the newly executed trace into this evidence directory.

Reproduce from the repository root:

```powershell
rtk proxy C:\Users\User\Desktop\myProject\his-poc\.venv\Scripts\python.exe scripts/test_with_postgres.py --pg-bin C:/Users/User/.cache/his-poc-tools/pg18/pgsql/bin -- C:\Users\User\Desktop\myProject\his-poc\.venv\Scripts\python.exe backend/tests/run_assistant_validation.py
```

These tests use explicit provider doubles, never a fallback model. Four real
profile qualification calls, protected URL testing and deployment are **NOT_RUN
by this backend worker** and remain with the root integrator. The root's exact
provider/schema dependency `e0531d89a5be0a6c10a1e292d53048c0b5f06d4e` was
cherry-picked under explicit parent authorization for offline integration tests;
this worker did not edit that dependency's source files.

The eligibility predicate excludes closed, completed, discharged and cancelled
visits, matching admission. The feature flag controls `config.enabled` while
preserving role-capability metadata. Production admission reads its clock after
the global PostgreSQL lock; the worker starts its lease from a fresh clock after
all authorization, collection and admission waits. No DB transaction is held
across provider network work. Legacy live inference inserts its new run only
after the shared admission lock returns, so its created-at lease also starts
after the wait. Existing legacy records are unchanged.

`backend/tests/export_assistant_qualification_packets.py` separately exported
four authored synthetic packets from a disposable database for the root's
private real-model qualification. Visit/nursing packets include a short Thai
note created through the normal document service. Their compact views are
1215/1083/583/608 bytes and complete input texts 1827/1707/1223/1250 bytes.
The private export and SHA receipt live under the root's ignored `var` directory,
contain no session credentials, and were prepared with zero model calls and zero
production database queries. The receipt preserves the exact source hashes at
export time; later eligibility/clock repairs do not rewrite those frozen inputs.

The worker requires `configured`, `qualified`, and the run's explicit membership
in `profiles_qualified`; an empty list qualifies no profile. No qualification-mode
public bypass is present. Timeout/interrupted attempts retain admission hold,
failed attempts are not automatically retried, and unchanged watch scans enqueue
nothing. No GET endpoint initiates preparation.

Schema 0005 changes candidate readiness. The root integrator must complete the
schema-compatible rollback image and deployment validation before migrating any
server database. No server, original DR/LabClear repository, production database,
remote repository or Cloudflare configuration was changed by this worker.
