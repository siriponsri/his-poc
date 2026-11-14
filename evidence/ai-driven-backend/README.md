# Assistant backend foundation evidence

Status: **OFFLINE BACKEND PASS; RELEASE NOT QUALIFIED**.

The candidate adds the four frozen preparation profiles, five additive tables,
scoped APIs, durable worker/watch polling, shared legacy/assistant admission,
and atomic reviewed document-draft/task effects. Existing source, inference,
proposal and committed-result tables are preserved.

Executed on an isolated, loopback-only PostgreSQL 18.6 database named `his_test`:

- Alembic migration to `0005_assistant_workspaces`: PASS.
- Alembic schema drift check: PASS, no new upgrade operations.
- 99 tests: PASS, zero failures: 49 assistant, 18 existing core, 32 existing
  document-provider tests. See `pytest-results.xml` for individual cases.
- Existing document review and provider tests are included in that total.
- Full canonical compact inference view is bounded to 2000 UTF-8 bytes. Notes
  are included whole or explicitly omitted; all eligible source evidence remains
  in the server-side manifest and freshness digest.

`execution.json` records commands, exit codes, timestamps and exact backend
source hashes. `executed-core-journeys.json` contains this run's existing-domain
regression trace. The repository's historical core trace was restored after
copying the newly executed trace into this evidence directory.

Reproduce from the repository root:

```powershell
rtk proxy C:\Users\User\Desktop\myProject\his-poc\.venv\Scripts\python.exe scripts/test_with_postgres.py --pg-bin C:/Users/User/.cache/his-poc-tools/pg18/pgsql/bin -- C:\Users\User\Desktop\myProject\his-poc\.venv\Scripts\python.exe backend/tests/run_assistant_validation.py
```

These tests use explicit provider doubles, never a fallback model. Real provider
input/output integration, exact provider system-prompt/context budget, four real
profile qualification calls, protected URL testing and deployment are **NOT_RUN
by this backend worker** and remain with the root integrator. The provider/schema
dependency is deliberately not created or copied by this branch. Runtime imports
are deferred until worker/config use so the integrator can supply those modules.

The worker requires `configured`, `qualified`, and the run's explicit membership
in `profiles_qualified`; an empty list qualifies no profile. No qualification-mode
public bypass is present. Timeout/interrupted attempts retain admission hold,
failed attempts are not automatically retried, and unchanged watch scans enqueue
nothing. No GET endpoint initiates preparation.

Schema 0005 changes candidate readiness. The root integrator must complete the
schema-compatible rollback image and deployment validation before migrating any
server database. No server, original DR/LabClear repository, production database,
remote repository or Cloudflare configuration was changed by this worker.
