# CareBalance LabClear gateway evidence

All records in this directory are synthetic engineering evidence. No owner
runtime, active database, environment file, model, DNS or deployment was changed.

## Accepted gateway and recovery phase

`pg-accepted-recovery-http.txt`, its JUnit XML and result JSON record **32 tests
and14 unittest subtests PASS**, one existing Starlette/httpx deprecation warning,
exit0. PostgreSQL18.6 was a new loopback-only disposable cluster. Its11 captured
source hashes had zero drift during execution.

The run covers15 controlled gateway tests,15 actual PostgreSQL gateway cases and
two real HTTP cross-application tests. The HTTP cases use the actual HIS session,
CSRF, PostgreSQL gateway and frozen LabClear client, calling a separate process
running the real LabClear connector routes with fresh encrypted SQLite test state.
They do not use a mocked receiver response. The receiver child and disposable
PostgreSQL processes were stopped by their owning fixture/wrapper.

New acceptance includes:

- Exact original import/confirm command recovery after losing browser state,
  with no automatic resend and no foreign actor/session access.
- Active lease handling and a different-key mutation fence while an original
  mutation remains unresolved.
- Scope filters before row locking, verified while foreign task/source rows
  remain locked in another transaction.
- Human correction and immutable confirmed readback, while the HIS released
  source and explicit review task remain unchanged.
- In-flight authorization/source/task changes quarantining actual receipts;
  late draft reads cannot regress a confirmed binding.

The subsequent packaged-PostgreSQL test adds a conditional storage assertion to
the shared cross-app test helper. This is a test-only phase change, recorded in
the later source snapshot; the accepted gateway implementation is unchanged.

## Exact deployment package, separate PostgreSQL receiver phase

`packaged-postgres.txt`, XML and result JSON record **two tests PASS**, one
existing dependency warning, exit0 and zero captured source drift.

The test builds and extracts the exact19-file allowlisted package, validates all
manifest hashes, explicitly invokes `carebalance_receiver.py prepare` and serves
the exact `carebalance_receiver:create_app` entrypoint from a temporary directory
without `.env`. It uses a separate newly created PostgreSQL database named
`carebalance_labclear_test_packaged_roundtrip`; HIS remains in `his_test`.

A deliberately mismatched PostgreSQL identity is rejected before receiver tables
can be created in HIS. The accepted real HTTP journey imports source values,
confirms a human correction, retries the exact command and reads the same result.
Foreign actors/sessions and unauthenticated receiver requests are denied. Receiver
ordinary `report` entities remain absent; neither application's tables appear in
the other's database. The server process and disposable cluster were stopped.

`packaged-receiver-candidate.json` records a deterministic package reconstruction
after this run. Archive SHA-256:
`a1d17b830914d09934a4400add6815cb585385dac8fd58f3386fe1364f3091fb`.
It contains19 files and143360 bytes. This binds source packaging, not a running
deployment image.

Python socket egress in the test child is denied; libpq is separately restricted
by the explicit loopback URL and actual database identity check. No OCR or model
route is mounted, and provider/external-business flags are false. This is not a
claim of a host firewall test or clinical/model effectiveness.

## Historical failures retained

`pg-recovery-http.*` retains two controlled fake-session scope subtest failures
after SQL scope filters were introduced; real PG/HTTP cases passed. The explicit
defensive scope check was retained as well as SQL filtering.

`pg-frozen-recovery-http.*` retains five controlled fake-session queue failures
after the new pending-attempt lookup was added. The fake fixture was updated for
the new query and a dedicated pending fence test added. Actual PG/HTTP cases
passed in that run. Neither failed run is final acceptance evidence.

Earlier `pg-initial.*`, `pg-final.*` and `unit-final.txt` retain their original
pre-recovery scope. Do not add their counts to current checks or describe their
mock transport as actual HTTP receiver execution.

## Still outside this evidence

Browser acceptance of the new HIS panel, server deployment/backup/migration,
Cloudflare protected connector workflow, full-system regression and clinical
effectiveness require their own evidence. Run the final migration metadata check
and appropriate all-domain regression before release. No Git staging, commit,
push or deployment was performed by this gateway task.
