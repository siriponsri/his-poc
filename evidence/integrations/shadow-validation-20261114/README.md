# Private deployment validation, 2026-11-14

Scope: fresh synthetic HIS + LabClear receiver on dr-train, project `his-poc-carebalance-validation`. No production activation, DNS/Access change, live inference, original DR runtime or original LabClear runtime changes were made by this validation work.

## Executed checks

Commands ran from the HIS repository through the local RTK shell wrapper. The ignored private helper sent bounded Python over verified SSH stdin; compose environment and synthetic credentials were not printed.

```text
rtk proxy python var/carebalance-integration/shadow_ops.py rollback
rtk proxy python var/carebalance-integration/shadow_ops.py prepare
rtk proxy python var/carebalance-integration/shadow_ops.py journey
rtk proxy python var/carebalance-integration/shadow_ops.py rollback-test
rtk proxy python var/carebalance-integration/shadow_ops.py preservation
rtk proxy python var/carebalance-integration/shadow_ops.py verify-images
rtk proxy python var/carebalance-integration/shadow_ops.py inventory
```

Each listed final invocation exited 0 and produced the corresponding receipt below. Receipts are sanitized operator assertions and measured outputs, not full HTTP request logs or a public clinical acceptance report.

| Receipt | Result and limit |
| --- | --- |
| `rollback-build.json` | PASS: copied frozen source, single readiness patch, compatibility image built; runtime not yet tested at that checkpoint. |
| `rollback-image-source-binding.json` | PASS: actual old and compatibility images, 214 source hashes, only main.py changed, 17 identical assets, network disabled. |
| `shadow-prepare.json` | PASS: fresh HIS and named receiver databases explicitly prepared; both readiness endpoints passed. |
| `shadow-api-journey.json` | PASS: 14 scoped checks across real candidate Linux images, HTTP and PostgreSQL. Human lab release42, receiver correction43, explicit confirmation/readback/retry, auth boundaries, source/task preservation. |
| `rollback-runtime.json` | PASS: compatibility image ready on the same0003 DB, ordinary auth/read/write, new gateway unavailable; new candidate restored. |
| `production-preservation.json` | PASS: 9 comparisons against prior production baseline, 109 table counts preserved, 3 selected results, 181 prior sessions, file/account scopes unchanged; original3 container IDs/images preserved. |
| `shadow-final-inventory.json` | PASS: exact new candidate/receiver image IDs, all3 shadow services running, only loopback18180/19190/15434, two distinct databases. |

The actual first preparation attempt did **not** pass: PostgreSQL's temporary UNIX-only initialization server initially satisfied `pg_isready` and restarted before the next SQL command, which reported `database system is shutting down`. The helper was repaired to require TCP readiness with `pg_isready -h 127.0.0.1`; preparation was rerun successfully against the retained fresh validation volumes. No volume, database or production resource was reset. This initial diagnostic is reported from the captured tool result, not reconstructed as a raw server log.

The image build log remains private at `/home/chaw/his-poc/var/carebalance-shadow-validation-20261114/rollback-build.log`. Private synthetic client credentials and browser source URL are in local ignored `var/carebalance-integration/shadow-client-private.json`. Do not publish either private environment or identity files.

## Current handoff

The restored candidate is `his-poc-server:workspace-07a719f2bee4`, exact ID `sha256:590304cabbf699b67b2af059fd80d088497d41fe541b66d134ad8797ca4cf6ed`. Receiver `his-poc-labclear:source-c1944c772e87` has exact ID `sha256:d02a78be86e67d8fc64f5133ceb5a07ab2270b4e97ad44f4fa518748da539b6f`.

Parent browser work may use an authenticated SSH forward to `127.0.0.1:18180` and the private client info file. The second released synthetic D10 source was created for that manual UI review. Browser/public acceptance is NOT_RUN by this agent. No model requests were made; receiver inference is disabled and HIS inference count remained zero.

Validation databases `his_shadow` and `carebalance_labclear_test_shadow` are distinct databases in one fresh validation-only cluster, using the same validation admin role. Do not treat this as proof of production credential/cluster isolation. No clinical accuracy claim follows from synthetic ALT range comparison or UI review.

See [RECOVERY_0003.md](../../../docs/integrations/RECOVERY_0003.md) for the rehearsed recovery procedure and its untested production limits. Preserve shadow volumes and private credentials pending the parent's acceptance decision.
