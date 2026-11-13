# Operations entrypoint

Current application runbook: [OPERATIONS_FULLSYSTEM.md](OPERATIONS_FULLSYSTEM.md) and [START_HERE.md](../START_HERE.md). Default is PostgreSQL18/FastAPI on a loopback entrypoint. Legacy stdlib/SQLite commands are historical regression only; they do not launch the current application.

First install: database ready → explicit migration → explicit seed → app ready. Restart does not seed/reset. A failed migration stops initialization before seed/application. Native development is intentionally selected with DATABASE_URL; no fallback to SQLite.

Use backup.py/restore.py only as documented. Restore target must be an isolated new database/file root; compare DB inventory and file hashes, not only command exit. Never call backup complete when referenced file bytes are missing. Current executed restore evidence is in VALIDATION_REPORT. Production HA/KMS/retention/recovery objectives remain UNKNOWN.
