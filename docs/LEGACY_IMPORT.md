# Legacy SQLite evidence import

This is an explicit, forensic **read-only archive** migration. It imports all 12 known v0.1/v0.2 tables into PostgreSQL `legacy_imports` and `legacy_rows`, retaining each original row, string ID, version, hash, approval, result, audit and idempotency payload. It never converts legacy users into working accounts or old proposals into executable v2 proposals. New shared-core workflows use new immutable revisions.

Stop the old server and make a closed SQLite copy with no outstanding WAL/journal. Keep the original unchanged. Inspection uses SQLite read-only/query-only mode, integrity checking and a before/after file SHA-256 check; it never initializes the old app or seeds/migrates source data.

```bash
python scripts/import_legacy.py /path/to/closed-copy.sqlite3 --report var/legacy-inspection.json
```

Inspect the source counts, schema, unimported extra tables and gaps. A proposal whose historical document text was overwritten is `evidence_unavailable`; its result/review records retain the same gap. The current document is stored as the current legacy row only. The tool never substitutes it for a missing historical revision or changes an approved hash. Invalid action hashes and broken references are retained as quarantine findings.

To archive into the explicitly configured PostgreSQL database, supply a JSON mapping from original patient ID to an existing current patient ID in the operator's active organization/facility. Mapping is never inferred from a name. Missing mappings remain quarantined from patient-facing read access. An empty mapping is allowed for evidence preservation but provides no patient read endpoint access.

```json
{"p-demo":"the-current-patient-id-confirmed-by-the-operator"}
```

```bash
# DATABASE_URL must already point at the target PostgreSQL database.
python scripts/import_legacy.py /path/to/closed-copy.sqlite3 --report var/legacy-import-report.json --mapping var/patient-mapping.json --apply --username system_admin --facility-id facility-demo
```

The CLI verifies the local account's password interactively (or reads `HIS_IMPORT_PASSWORD` for isolated automated tests), uses server memberships and requires D38 write permission. It creates a short-lived session for current authorization checks and revokes that session in the same successful transaction. This is a local operator tool requiring target DB access, not a public upload endpoint. The imported source file is not bundled by the tool.

The whole archive+audit is one PostgreSQL transaction. A source SHA-256 is unique per organization/facility; same source+same mapping returns the existing import, while a different mapping conflicts. A PostgreSQL advisory lock handles concurrent imports of the same source. `legacy_rows.id` provides the new archive identifier; `import_id`, `source_table`, `legacy_id` preserve the exact original-to-archive mapping. These are archive IDs, not live clinical entity IDs.

`GET /api/v2/legacy/results?patient_id=...` requires D22 read plus current patient/organization/facility scope. It returns only archived results mapped to that patient, marked `read_only`, with source identity and missing-evidence gaps. Legacy commit always fails with `LEGACY_EVIDENCE_READ_ONLY_NO_NEW_COMMIT` after authorization. Reading a prior result does not replay an old database write or reissue a transaction.

Verification: six stdlib inspection tests cover exact IDs/JSON strings/hash preservation, unavailable overwritten evidence, invalid hash quarantine, orphan retention, WAL rejection and repeatability. Four PostgreSQL tests cover persisted archive/reconnect, idempotent import, scoped read/commit denial and changed mapping/revoked permission, and real CLI account verification/session revocation. See `evidence/fullsystem/baseline/legacy-import-pg.txt` for actual execution; a test's presence alone is not PASS.

Legacy result content additionally requires `documents.content`; a billing/auditor metadata-only `D22.read` grant cannot retrieve archived narrative results.
