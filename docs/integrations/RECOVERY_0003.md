# Recovery for connector migration 0003

Verified 2026-11-14 on a fresh, private dr-train validation deployment. This is a recovery rehearsal, not production activation or a completed public acceptance test.

## Preserve the schema and evidence

`0003_carebalance_integrations` adds `connector_bindings`, `connector_attempts`, `connector_exchanges`, their indexes, and evidence protection functions/triggers. It does not alter the earlier tables. Its downgrade deliberately raises an error: connector source snapshots and outcomes require a reviewed archival migration. Do not remove those tables or downgrade the database to recover an application release. Do not restore an earlier database snapshot over records written since that snapshot.

The unmodified previous application requires migration `0002_live_inference` in its readiness check. Consequently, selecting its old image alone against migration 0003 will fail readiness even though the migration is additive. This limitation was confirmed in the previous frozen source; it is not a claim that an old-image outage was induced in production.

## Prepared compatibility image

| Item | Verified value |
| --- | --- |
| Original frozen source | `/home/chaw/his-poc/releases/workspace-167d14addf47` |
| Separate compatibility source | `/home/chaw/his-poc/releases/rollback-0003-8b91c19e32fe` |
| Compatibility image | `his-poc-server:rollback-0003-8b91c19e32fe` |
| Exact image ID | `sha256:590f3b505e4ce7617e60376d14d42db3850a2eb1d261f2d6cdf0ec0d17ece13c` |
| Patched main.py SHA-256 | `8b91c19e32fe527ab36e252cb2504c2fd6034a2a572fbc8bdb1c5b747336eee7` |

The previous frozen source and image were retained unchanged. Only the copied `backend/app/main.py` readiness condition changed from accepting only 0002 to accepting either 0002 or 0003. Image inspection with network disabled compared all 214 source files and 17 built assets: only that source file differed and every built asset matched. This image provides the prior UI and core application behavior; it does not expose the new LabClear gateway.

The private rehearsal switched only the validation application to the compatibility image while retaining the same migrated database and LabClear containers. Readiness on 0003, ordinary login, existing patient/document/task reads, and an authored synthetic document write/readback passed. Connector rows remained present. No schema restore or downgrade was performed. The new candidate was restored and readiness passed afterward. See [rollback-runtime.json](../../evidence/integrations/shadow-validation-20261114/rollback-runtime.json) and [rollback-image-source-binding.json](../../evidence/integrations/shadow-validation-20261114/rollback-image-source-binding.json).

## Operator recovery sequence

1. Confirm the actual active application image, database revision, connector receiver image and scoped compose project. Retain current database/file backups and deployment evidence. This rehearsal did not authorize a production recovery action.
2. For a connector-only problem, disable the integration on the current application using the reviewed deployment configuration and recreate only that application service. Retain the receiver database, HIS connector evidence, and clinical source records. Confirm core application readiness and login. This feature-disable path was not exercised in this private rehearsal.
3. For a core application regression after 0003, select the exact compatibility image above using a separate reviewed app-only override. Keep the current database, volumes, secrets, connector receiver and Cloudflare connector unchanged. Recreate only the named HIS application service. Do not run seed, downgrade or restore commands on a live database.
4. Confirm `/ready` reports migration 0003, login and existing-record reads work, and the expected prior UI assets are served. Expect the new LabClear gateway routes to be unavailable. Preserve unsuccessful connector attempts for investigation; do not interpret a missing gateway as a completed or rejected remote operation.
5. Reconcile any unknown connector outcomes before retrying. A retry must preserve its original operation identity; it must not create a second clinical action or overwrite the released HIS source. Returning to the new candidate is an app-only replacement after review of its exact image ID, followed by readiness and scoped smoke checks.

Production recovery commands are intentionally not automated here: the parent release procedure owns the actual active compose files and final activation. The tested private project is `his-poc-carebalance-validation`; it must never be mistaken for `his-poc-server`.

## Boundaries of the evidence

- PASS: private Linux candidate HTTP workflow, separate named HIS/LabClear databases, same-key retries, actor/session/patient/CSRF denial, unchanged released HIS source, open review task, compatibility recovery and candidate restoration.
- PASS: original production container IDs/images and previously recorded results, files, account scopes and sessions preserved during this rehearsal. Production still reported migration 0002 at the preservation checkpoint.
- NOT_RUN here: public URL/browser acceptance, production migration/activation, external providers, clinical accuracy or model inference. Provider mode was `mock_demo`; the receiver reported inference disabled and the private HIS database retained zero inference runs.
- The validation databases share one new PostgreSQL cluster and its validation-only admin role. This is not evidence of production credential or cluster isolation. Production must follow the dedicated receiver deployment contract.

Keep the private credentials and operator files under ignored `var/`; do not copy them into this document or evidence. Preserve the private validation volumes until the parent decides the rehearsal can be retired.
