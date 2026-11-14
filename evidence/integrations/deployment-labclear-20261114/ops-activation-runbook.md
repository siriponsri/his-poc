# Dedicated receiver activation receipt

Parent-authorized operation on dr-train, 2026-11-14. The frozen application and receiver were activated on the existing `his-poc-server` project. This operator did not run the public browser journey or model inference.

## Actual state at handoff

| Item | Observed value |
| --- | --- |
| HIS image | `his-poc-server:workspace-5328d8216f0f` |
| HIS image ID | `sha256:a57b43d918bbbfe05cc444c1273ae952a46407efef017631bbd15f8c7b5b4ee6` |
| Receiver image | `his-poc-labclear:source-c1944c772e87` |
| Receiver image ID | `sha256:d02a78be86e67d8fc64f5133ceb5a07ab2270b4e97ad44f4fa518748da539b6f` |
| Migration | `0003_carebalance_integrations` |
| Receiver DB / role | `carebalance_labclear` / `carebalance_labclear` |
| Receiver database volume | `his-poc-server_labclear_database` |
| Readiness | HIS + receiver ready; all five named services healthy |
| Receiver process UID | `10001`; image USER `10001:10001` |
| Origin ports | HIS18080, HIS PG15432, receiver18090, receiver PG15433, tunnel metrics20331, all127.0.0.1 |
| Rollback executed | No |

The existing HIS database and Cloudflare connector container IDs/images were preserved. Every other pre-existing container ID was also unchanged at verification, including the validation stack and existing model services. No seed, live database restore, original LabClear account/runtime change, DNS/Access change or model request was performed.

The 05:35:43Z preservation checkpoint passed all14 checks: all109 earlier table counts were exactly equal,112 total tables with the three new connector tables empty, all181 prior session hashes exact, three selected committed results preserved, file hashes unchanged, test account password hash/permissions/care scope unchanged, inference count unchanged and four Cloudflare HA connections. Source231 files and dist17 assets matched the frozen candidate. All17 assets also returned200 with matching bytes from loopback HTTP. Subsequent parent browser activity can legitimately add scoped synthetic records/sessions; this receipt describes that exact checkpoint.

## Private configuration and future operation

Deployment root: `/home/chaw/his-poc`. The original `var/server.env` and base `deploy/dr-train/compose.json` remained byte-for-byte unchanged. The reviewed `deploy/dr-train/compose.labclear.json` was copied from the frozen release; SHA-256 `4ef28599fa37281f42ee5a05b7827d67335f288ce0d143e00715ce8eda40fd88`.

The new server-only `var/labclear.env` is0600. It contains final HIS/receiver image selections, the explicit integration toggle and independently generated database, connector and data-encryption secrets. Those values were never printed or committed. Future operations must use **both env files in order**, and both compose files:

```sh
docker compose --project-directory /home/chaw/his-poc \
  --env-file /home/chaw/his-poc/var/server.env \
  --env-file /home/chaw/his-poc/var/labclear.env \
  -f /home/chaw/his-poc/deploy/dr-train/compose.json \
  -f /home/chaw/his-poc/deploy/dr-train/compose.labclear.json \
  ps
```

`ps` is read-only. Do not rerun deployment helpers to inspect status. Base-only startup still selects the older image from the retained server.env; after migration0003 that unmodified older image does not satisfy readiness. Use the layered profile above and an explicitly reviewed application selection.

Runtime phase state is private under `var/labclear-activation-20261114/`. Each mutation phase writes a RUNNING sentinel before its first action and refuses a repeated phase. If a client timeout occurs, inspect the ledger and actual containers before any continuation. Never assume a failed SSH call means the server action was not executed.

## Backup and restore proof

Backup: `/home/chaw/his-poc/var/backups/pre-labclear-20261114T053020Z`.

- `his_poc.dump`:706777 bytes, SHA-256 `b5b55176f6d70cb5a0691a6bd3e903a25ab1a9eec28183a795f039bdb910841f`.
- `files.tar`:10240 bytes, SHA-256 `01c6b11bed9cc7405f8007434af90baf8992951bdf36b9096d2376be12aff4b2`; each archived file matched its baseline content hash.
- Private0600 copies of server.env, base compose and the named tunnel config/credentials retained; their hashes were verified again after activation. Secret contents were not exported.
- The actual dump was restored with `pg_restore --no-owner --no-privileges --exit-on-error` to a **new** database `his_predeploy_restore_20261114053021` in the validation-only cluster. All109 table counts exactly matched and revision0002 was confirmed. No existing database was overwritten or dropped. Restored data was retained.

The logical dump and file archive were obtained as separate operations. Their hashes and restore results establish recoverability for this synthetic checkpoint, not a general atomic backup guarantee under arbitrary concurrent writers.

## Executed sequence and diagnostics

All local commands used `rtk proxy python var/carebalance-integration/activate_labclear.py PHASE`. SSH used the known dr-train key with strict host checking; Python was sent through stdin. No old `selected_release_ops.activate` call was made.

| Actual phase invocation | Exit / result |
| --- | --- |
| `preflight` | 0 / PASS: original0002 state, exact images/source/assets, free dedicated ports. |
| `backup` | 0 / PASS: fresh dump/archive/private config backups and actual isolated restore. |
| `receiver` | 1 / failed before first service start: default compose config omits the profiled connector; equality guard raised KeyError. Reviewed overlay and new private env had been written. |
| `reconcile-receiver` | 0 / PASS: actual original IDs/readiness unchanged, no new receiver container/volume; retained failure ledger and generated environment. |
| `continue-receiver` | 0 / PASS: configuration comparison included the public profile; only new receiver DB and receiver were started, explicit prepare succeeded. |
| `activate` | 0 / PASS: explicit candidate Alembic upgrade then app-only replacement; no seed or rollback. |
| first `verify` | 1 / metadata guard failed: Docker USER was10001:10001 rather than the narrower expected10001 string. No runtime failure or service repair. Source/dist/preservation checks before this guard passed. |
| `reconcile-verification` | 0 / diagnostic retained with FAIL metadata-guard status; actual UID10001, correct receiver image and healthy services confirmed. |
| second `verify` | 0 / PASS: new readonly verification phase, exact hashes, all14 preservation checks and listener/health/config/backup checks. |
| `inventory` | 0 / PASS: readonly existing synthetic patient001 labs/tasks; no rows created. |
| `logs` | 0 / PASS: exact migration and receiver preparation stdout/stderr exported only after screening against configured secret values. |

Actual mutation commands were: receiver DB `up -d --no-deps labclear_db`; explicit receiver `run --rm --no-deps labclear python carebalance_receiver.py prepare`; receiver `up -d --no-deps labclear`; candidate `run --rm --no-deps app python -m alembic -c backend/alembic.ini upgrade head`; then `up -d --no-deps --wait --wait-timeout90 app`, using the layered compose prefix above. PostgreSQL TCP readiness was checked explicitly before prepare. The full profiled config was rendered privately to verify db/connector equality and preserve all original application environment settings, including AI settings; `--profile public` was used for comparison only, not to recreate the existing connector.

## Recovery selection

The tested compatibility image remains `his-poc-server:rollback-0003-8b91c19e32fe`, exact ID `sha256:590f3b505e4ce7617e60376d14d42db3850a2eb1d261f2d6cdf0ec0d17ece13c`. It was previously rehearsed on the private migrated DB. The activation helper prepared an app-only private override at `var/labclear-activation-20261114/rollback-only.json`; no rollback was required here.

If application recovery is authorized, use the same layered configuration with that additional override, recreate only `app`, and verify0003 readiness/login/core reads. Keep the live database, connector evidence, dedicated receiver, files and Cloudflare connector. Do not downgrade0003 or restore an old backup over newer clinical records. The compatibility UI intentionally lacks the new gateway. See the separate [recovery rehearsal](../../../docs/integrations/RECOVERY_0003.md) for its exact source patch and prior runtime evidence.

Public authenticated workflow acceptance and any clinical/model evaluation remain separate parent tasks. The readonly inventory shows six existing corrected/v10 synthetic lab sources and no review task at this checkpoint; the parent can create one explicit review task against a selected existing source rather than duplicating the lab result.
