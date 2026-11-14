# HIS DR bridge implementer qualification

Base: `0c003e753a5e93520780beca55e16078c1e34229`, branch
`feat/carebalance-dr-bridge`. No commit, merge, push or deployment by this worker.
Parent owns the frontend, exported contracts, operational provisioning and public
acceptance. Other parent frontend changes were preserved.

## Exact final result

- **PASS66/66**, zero failures/errors/skips:15 actual PostgreSQL gateway cases,
  50 strict sender tests and one real HTTP bilateral clinical workflow.
- **PASS44 ordinary tests +62 subtests**: existing LabClear gateway regression
  against the new0004 head. Only its explicit expected-head assertion changed
  from0003 to0004, with parent authorization. LC/auth/AI runtime source and
  migration0003 remain byte-identical.
- **PASS** additive nine-table migration,121 public tables including Alembic,
  and `alembic check`: no schema/model drift.
- **PASS** final11-file source snapshot before/after qualification is unchanged.
  New DR DTO module is byte-identical to the independent receiver's frozen
  `9601d4798163721f60fdf301ffbe3873a42ebfd1382cf323bc14e310beed0391`.

Machine receipt: [execution.json](execution.json). Exact final source hashes:
[source-integrity-freeze.json](source-integrity-freeze.json). Actual final test
output: [qualified-frozen-output.txt](qualified-frozen-output.txt), JUnit
[qualified-frozen.xml](qualified-frozen.xml). Earlier failures and intermediate
source phases remain separately named; their results are not promoted to the
final source. Independent review evidence is maintained separately by parent.

## Runtime delivered

Nine dedicated DR tables preserve authored source registration, immutable ordered
source sets and items, verified facility grants and their append-only lifecycle,
session-bound consent/bindings, commands, transport exchanges and report receipts.
The grant lifecycle trigger captures exact prior/new JSON, version, database
principal and timestamp. A direct SQL event does not invent a HIS human actor.
No default clinical grants or public grant-creation endpoint exists.

HIS revalidates current session, membership, patient/visit/task/source/order and
verified capability before each specialist request and after outbound work.
Grant/verifier rows remain locked during finalization. Commands reserve and
release their transaction before HTTP. Late/expired leases retain the actual
exchange as quarantined; another key cannot bypass unresolved mutations.

Sender checks literal loopback destination, exact configured clinical scope,
HMAC bytes, bounded replies, route MIME, original image SHA, case/member/patient/
visit/eye identity, immutable report/witness hashes, positive human milestones,
report findings and verified signer attribution. Missing or malformed evidence
cannot become a `CURRENT` assessment. Historical report/signature JSON remains
unchanged when other-eye review changes; assessment is separate metadata.

Protected HTML/assets/API/images/print run current HIS authorization. HTML injects
the agreed `carebalance.dr.browser.v1` context and a server-owned return URL with
opaque patient/visit/source IDs. Static assets must match an exact file manifest.
Unknown specialist paths cannot fall through to the generic HIS SPA. Print adds
a clear stored-report assessment note without changing immutable report JSON.

## Configuration and operator boundary

No receiver is selected from a browser URL. Provision an exact source-set scope
offline, then set `HIS_DR_ENABLED=true` and `HIS_DR_DESTINATIONS_FILE` to a private
absolute UTF8 JSON file. On Linux it must have no group/other permissions. Schema:

```json
{
  "version": 1,
  "destinations": [{
    "id": "carebalance-dr-his-poc",
    "origin": "http://127.0.0.1:18190",
    "key": "<private>",
    "scope": "<exact object returned by GET source-sets/{id}.scope>",
    "workspace_id": "cb-<first32 SHA256 hex of canonical scope>"
  }]
}
```

The illustration is deliberately invalid/redacted: generate a dedicated secret
of at least32 bytes on the server and supply the exact object, never the strings
shown above. Source-set creation may remain unprovisioned; import returns503
until registry scope/workspace matches exactly. Binding freezes a destination
fingerprint and cannot be retargeted by later registry edits.

`HIS_DR_WEB_MANIFEST` points to an absolute operator-owned JSON file with
`schema=carebalance.dr.web.v1`, an absolute `root`, and `assets` mapping complete
dist-relative paths to SHA256. Parent supplies the qualified derivative build.
HTML `./assets/` becomes the protected `/assets/assets/` path, preserving CSS
relative fonts and the exact manifest keys.

Authored provenance registration is an offline Python function only:
`dr_core.register_authored_source`. It verifies a released/current D11 source
against the exact generated fixture bytes, image hash and immutable explicit
eye/modality/capture metadata. Its evidence reference starts
`authored-synthetic:`. An ordinary PNG upload or browser checkbox is not synthetic
provenance. No original DR image/sample store or real patient image is used.

## Verified boundaries and limits

The actual HTTP test launches the independent derivative's own interpreter and
Uvicorn process, with a second dedicated database in the disposable PG18.6 test
cluster. It transfers two authored PNGs, explicitly assesses quality and confirms
image context, denies a generic clinician's grade/sign ability, then uses declared
synthetic verified grants to exercise grade, original-pixel annotation, report
sign/replay and persisted readback. Changing the other eye produces `CHANGED`
while preserving the signed report hash. Original HIS source bytes/versions and
open review task remain intact; inference count is unchanged.

This is local process/database integration evidence. It does not establish Linux
image activation, deployed/public browser acceptance, real clinical credentials,
retinal model inference or clinical effectiveness. The original DR repository and
runtime, existing LabClear deployment, DNS/Access and paid resources were untouched.
