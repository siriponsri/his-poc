# Read-only public journey database readback

Command actually run from the HIS repository:

```text
rtk proxy python var/carebalance-integration/public_labclear_readback.py
```

Exit0; database receipt observed at2026-11-14T05:46:01Z. This operator inspected database state after the parent's actual authenticated browser workflow. It did not perform a browser action, create a session, call a receiver route, consume a nonce, migrate, deploy or write a business record.

The helper executed SELECT-only, repeatable-read/read-only transactions inside the existing HIS and dedicated receiver containers. The receiver read used psycopg and the existing process environment to decrypt only the exact owned source/report/confirmation/idempotency/audit entities. It did **not** use `business_store.transaction()`, which performs schema/migration bookkeeping, or the HTTP read route, which consumes an authentication nonce. No secret, session token, ciphertext or decrypted unrelated account data was exported.

Results are in `public-readback-database.json`:

- PASS9 HIS checks: exact current source snapshot/hash matches the immutable binding, actor/session/patient/encounter ownership, canonical request and review hashes, one import and one confirmation, three successful attempts/exchanges, same-person confirmation and correction, identical confirmed explicit readback, unchanged source/order, open review task.
- PASS8 receiver checks: dedicated database/owner partition, encrypted report equals the HIS receipt, original cells retained, review hash, human actor/same-person binding, one import/confirmation audit each, durable idempotency receipts and one report without duplication.
- PASS6 preservation checks: all181 prior sessions retained, unchanged test account password hash/scopes, selected committed results and stored files, unchanged inference count, unchanged original DB/Cloudflare connector IDs/images.182 current sessions include the parent's fresh public login. The readback added none.

Source `118004b0-dca0-4519-8b47-3d6d6314ede4` remains corrected/v10, printed value6, source hash `2043dbd9eb0244bd767f46e3f81ba50e90c7c00f7cd25c42365aabeb6947bea4`. Its linked order remains completed/v4. Review task `c5ede7b8-6ba2-489e-9590-a3cf2de0039d` remains open/v1. Binding `c61fa41a-a340-41ca-8c19-38c3da27ac75` is confirmed. Human-reviewed value7 has revision1, reviewer `user-test01-poc`, corrected index0 and SHA-256 `2c2b022bdc7a598dd6374f2f3b5482748aa5ad7c8aa5c6fd53757ec672776967`. The separate transferred-cell snapshot hash is `84ef40c404b995d3042af77c7f8653a402dc297ff71c72280af6f670d6c5cf65`.

The receiver contains one report, one source, one confirmation, two durable idempotency records and three consumed nonces for this journey. HIS inference_runs remained9→9 from the preserved baseline, and the receiver's external/provider settings remained disabled. These are integration and preservation results; they are not clinical effectiveness, OCR or model evaluation results. The parent's `acceptance.json` and screenshots separately establish the browser observations.

Private server configuration file hashes matched before and after the readback. No runtime/service changes, Git staging or source edits were made by this readback task. The private ignored operator helper's exact hash and this receipt's artifact hashes are recorded separately for audit.
