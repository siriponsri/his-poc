# PostgreSQL and legacy migration

Current PostgreSQL schema is versioned by Alembic under backend/migrations. From package root with development DATABASE_URL:

```bash
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini check
```

Initial schema is a frozen migration snapshot, not dynamic create_all at app startup. SQL reference export is documentation, not the upgrade command. Seed runs explicitly after migration and preserves existing rows/grants. Restart does not seed/reset. Migration failure stops the launcher before seed/app startup.

The v0.2 SQLite database is not converted in place. Use a closed copy, preserve its original bytes/checksum, and follow LEGACY_IMPORT.md. The importer preserves all original rows/hashes/IDs and maps authorized subjects into a read-only forensic archive. Missing overwritten document revisions are evidence_unavailable; inconsistent/orphan evidence is quarantined, not repaired by inventing history. Legacy credentials are not imported as active logins. No new proposal commit can use that unavailable archive.

Before upgrade: make verified DB+files backup and preserve app/schema version. Restore drills use isolated new targets. Do not point v0.2 binaries at PostgreSQL or a new schema; rollback to old source with new database state is not supported. For a real subsequent release, create a new Alembic revision; do not regenerate/rewrite a migration already applied by a user. The initial snapshot was revised only during this unreleased isolated development round.

Actual migration/restore verification is reported independently from metadata-created importer tests and isolated SQLite regression.
