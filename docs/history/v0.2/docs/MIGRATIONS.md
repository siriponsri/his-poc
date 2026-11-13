# v0.1 → v0.2 demo schema migration

The backend performs one additive migration in `Service.__init__` inside the same `BEGIN IMMEDIATE` transaction as initialization:

```sql
ALTER TABLE runs ADD COLUMN abstain_reason TEXT;
```

It first checks `PRAGMA table_info(runs)`, so the statement runs only when needed. Existing rows retain NULL. No reason is reconstructed from other data, and no patient/encounter/task rows are imported. Concurrent initialization is serialized by SQLite. Initialization no longer uses `executescript`, which would commit before the migration.

Only a newly created tasks table receives `task-demo`. Restarting an existing database does not reopen a completed/cancelled task or recreate a deleted task. Generic task binding and versioned migration tooling remain subsequent work.

Before using an existing demo database: stop the server and keep an unchanged backup, then start v0.2 against a copy using HIS_DB_PATH. Verify integrity and row counts and preserve the original. Do not point v0.1 binaries at the migrated copy: the older code uses positional INSERT without the added column. Rollback means running v0.1 against its pre-migration backup; preserve post-upgrade output separately for reconciliation.

Executed migration regression: `test_old_run_table_is_migrated_once_without_inventing_reason_or_reopening_task` in `tests/test_service_regressions.py` exercises a v0.1-shaped runs table, concurrent initialization, NULL preservation, one added column and retained cancelled task state. This synthetic regression is not a production migration/backup drill.
