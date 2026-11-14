# Selected workspace release: deployment readiness

This records the first selected-workspace activation. The later owner-requested
wide patient panel supersedes its active image; see `patient-panel/READINESS.md`
and the separate receipts there. Earlier observations below remain point-in-time
evidence and are not rewritten as later public acceptance.

Prepared 14 November 2026. Scope: replace only the dedicated HIS application with
the owner-selected Clinical Workspace home, Patient Record screens and Operations
Desk logo. The owner authorized deployment to https://his.ai-cie.com. The parent
integrator must freeze and review the actual candidate before activation.

## Current verified boundary

`baseline-readiness.json` records a fresh read-only inspection of dr-train:

- Dedicated app, database and connector are healthy; migration0002 is ready.
- Current rollback image: `his-poc-server:triadic-778ba97bf46f`.
- Image ID: `sha256:6144c7744b6976c8f0c142486acc4baaa283f0515f1d36c3a951337e53773935`.
- Application18080, PostgreSQL15432, Ollama11434 and connector metrics20331 listen
  only on127.0.0.1. Connector reports four HA connections.
- All109 public table counts, one stored file checksum, both prior committed
  live-model results, test01 clinician/patient-001 scope and178 session rows are
  retained as the comparison baseline. Authentication material remains private.

This is readiness evidence. It is not evidence that the new interface is deployed,
nor a new inference or authenticated browser acceptance result.

## Activation sequence after the integrator freezes the candidate

1. Confirm frontend checks/review and unchanged backend/deployment configuration.
   Self-hosted fonts must be WOFF/WOFF2 or included explicitly by the snapshot
   allowlist. The current allowlist excludes TTF.
2. Run `scripts/dr_train_deploy.py validate`; create a unique current-source archive
   and source-hash manifest. Verify the complete allowlist and local asset hashes.
3. Transfer the archive privately to a unique server release directory; verify
   archive and every manifest source hash before building an immutable image tag.
   Build without altering running containers. Retain a bounded build log.
4. Immediately before replacing the app, export a fresh PostgreSQL custom-format
   dump, copy/hash the stored file and capture read-only table/account/session/
   prior-result state. Retain this backup under the server private backup root.
   Do not seed, reset, restore or modify accounts.
5. Change only private `HIS_DEPLOY_IMAGE` and recreate only Compose service `app`
   using `up -d --no-deps --wait app`. Do not restart database or connector; do not
   reroute DNS or alter Access, Ollama or unrelated services.
6. Verify health, migration, no-store, runtime source and built-asset hashes;
   compare prior committed results, file, account and all preexisting session rows.
   Confirm database/connector container IDs and start timestamps remain unchanged.
   Repeat private listener/resource/HA checks.
7. Parent integrator checks unauthenticated Access gating and authenticated Login,
   Home, Patient Record and synthetic document/real-AI/human-review flow through
   the actual public URL. This browser evidence is distinct from server readiness.

## Stop conditions and rollback

Stop activation on manifest/build/check failure, unreviewed source drift, absent
fresh backup, unexpected schema/configuration change or missing preserved state.
If the replacement is unhealthy or public acceptance fails, restore only private
`HIS_DEPLOY_IMAGE` to the exact retained rollback image above and recreate only
`app`. Retain database/files and all evidence; do not restore the active database.
No rollback execution has been necessary or claimed for this release.

## Frozen image built, awaiting activation

The first source snapshot was held before transfer/build when the integrator
requested canonical D01/D03 context URL fixes. It remains explicitly superseded in
`superseded-snapshot-phase-boundary.json`; no image or activation used that archive.

The replacement freeze matches
`apps/web/evidence/research-ui-20261114-final/checks.json`:25 unit,76 component,
3 audit cases, typecheck and build passed. Its212-file archive SHA256 is
`072a759f371d7c77d50edb5ce1bb5fe14907ba7ba6889b6d04e4bf027aff19bf`.
Immutable candidate: `his-poc-server:workspace-072a759f371d`, image ID
`sha256:cd6f108817aa65663c7bc2842bcc40242356b15924015a7a266e62a1e5aae211`.

`built-image-source-binding.json` verifies all212 source hashes and17 built assets
against Windows. This used a disposable, network-isolated, read-only inspection
container; it did not start the application or connect to PostgreSQL/Ollama.
The image includes all three WOFF2 fonts, their OFL licenses, the selected logo,
`index-3ptj9r2B.css` and `index-DMoPMKHs.js`.

## Activated after independent review

The parent authorized activation after independent review of the final source and
rendered design. `activation.json` records the fresh private database/files backup
at `/home/chaw/his-poc/var/backups/pre-workspace-072a759f371d-20261114T020346Z` and
the successful replacement of only the app. No restore, seed, account reset or
connector restart occurred; rollback was not needed.

`postactivation-preservation.json` passes13 checks: health/readiness/no-store,
selected image, unchanged database/connector containers, both prior results, one
exact stored file, unchanged test account/scope, all178 prior session rows and
nondecreasing109 table counts, private listeners and four connector HA connections.

`runtime-source-binding.json` passes all212 active source hashes and17 built assets
against the frozen Windows source/build. Public unauthenticated HTTPS checks pass
for five paths, including an invalid Access assertion; all redirect to the expected
Cloudflare Access gate. See `public-access-boundary/access-boundary.json`.

Status: DEPLOYED_ORIGIN_VERIFIED. New authenticated public browser acceptance is
separate and pending the owner's Access sign-in; it is not implied by these checks.
