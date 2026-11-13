# HIS POC on dr-train

Target: https://his.ai-cie.com. Deployment root: /home/chaw/his-poc.
This is the server runtime root, not a Git checkout. Source releases are separately
verified snapshots under releases/. Private operator state stays under var/.

## Authorized boundary

The owner explicitly authorized deploying the HIS application and named Cloudflare
Tunnel on dr-train. Existing unrelated services, Ollama container, shared tunnels and
the Windows source database/files remain intact. Only the isolated his-poc-server
Compose project is managed by this runbook.

The first private/protected origin used the stable base39f788f image while the
new interface was developed. That baseline must not be called the final UI release.
Final candidate identity and actual external acceptance are recorded separately.

## Runtime topology

- App: Linux host network, explicitly binds127.0.0.1:18080.
- PostgreSQL18.6: isolated bridge, published only127.0.0.1:15432.
- Existing Ollama: unchanged host loopback11434, pinned Typhoon and engine0.12.6.
- Connector: Linux host network, exact hostname/Access team/AUD, final404 catch-all.
- Connector metrics:127.0.0.1:20331; path normalization enabled, debug diagnostics off.
- Secure / HttpOnly / SameSite=Strict application cookie, exact HTTPS allowed origin,
  no-store responses and a90-second external inference deadline.
- Pinned cloudflared2026.10.7 digest4955524aeaa379e154023d5a027c250f7b35041a2e7e950cf13f144bc9b9c5ba.
- Restart unless-stopped, bounded CPU/RAM/log size, read-only app/connector roots,
  no-new-privileges and dropped app/connector capabilities.

Host networking is selected because the existing Ollama endpoint is bound only to
host loopback and belongs to the default Docker bridge. The app command explicitly
binds loopback; host networking must never be combined here with0.0.0.0. The database
port is also loopback-only. No model or database public route is defined.

## Private files

var/server.env contains operator secrets and the immutable app image selection.
The named credential is /home/chaw/.cloudflared/b675e400-5731-47ba-9b4b-ce4d4056a3b2.json
with mode0600. Connector UID/GID1000 reads the credential through a read-only mount.
The existing token/run-tunnel.sh in that directory were not changed. No account-wide
certificate was copied to the server.

Use the existing functioning SSH host entry; the friendly dr-train alias initially
attempted the wrong user and failed. Do not weaken host-key checking or expose keys
to repair an alias. The deployment verified the actual hostname as dr-train.

## Reproduce the source snapshot

After the candidate frontend/backend is frozen, on the Windows checkout run:

    python scripts/dr_train_deploy.py validate
    python scripts/dr_train_deploy.py snapshot --output var/deployment-drtrain/CANDIDATE.tar.gz

This packages current working source, not merely HEAD. The allowlist excludes .env,
var, node_modules, built assets, evidence, temporary preview config, key files and
credential-named files. It records every source hash and rejects a changed source
during packaging. Never reuse an output filename. Transfer privately and verify the
manifest before building an immutable image tag under the server releases folder.

The baseline archive was deliberately generated from committed39f788f instead;
final delivery must use the current-working snapshot after the UI freeze.

## Compose operations

Set private HIS_DEPLOY_IMAGE to the reviewed immutable image. Do not print the
resolved Compose configuration because it contains the database and seed passwords.

    docker compose --project-directory /home/chaw/his-poc --env-file /home/chaw/his-poc/var/server.env -f /home/chaw/his-poc/deploy/dr-train/compose.json up -d --no-deps --wait app

The public connector is opt-in:

    docker compose --project-directory /home/chaw/his-poc --env-file /home/chaw/his-poc/var/server.env -f /home/chaw/his-poc/deploy/dr-train/compose.json --profile public up -d --no-deps --wait connector

Never run down -v. Avoid seed/reset on this restored database. Readiness checks
migration0002; apply explicit migrations only for an actual future schema change.

## Data migration and persistence

The source Windows PostgreSQL/files were read-only exported, not moved or reset.
Initial isolated restore verified all109 table counts, one exact file checksum and
the exact prior committed real-model result8d61f05f-6b07-45d6-8d76-dc3296693dbb.
A controlled restart of only the new app retained that result/action hash and file.

The first read-only probe used the wrong table name results; it was corrected to
the actual committed_results table without repeating restore. An initial
case-sensitive header dictionary lookup was likewise corrected; the actual
case-insensitive HTTP check confirms Cache-Control:no-store.

Server writes after this copy are independent of the Windows database. There is no
automatic bidirectional synchronization. Retain server backups before future
updates. Do not restore the source dump over the active server database.

The initial file volume was populated by a one-off authorized helper before
Compose labeled it, so Compose reports an existing-unlabeled-volume warning. Its
exact file checksum, mount and ownership were verified. Do not delete the volume
to silence that warning.

## Rollback

For a UI-only candidate, retain the prior image and change only private
HIS_DEPLOY_IMAGE back to that immutable tag, then recreate the app with the command
above. Database and file volumes remain attached. A schema-changing release needs
a separate reviewed migration/restore plan; this runbook does not roll back
historical database evidence or modify immutable results.

Stop only the named connector if public traffic must be halted. Do not alter other
Cloudflare tunnels, shared services or DNS records as a blanket rollback.

## Evidence and acceptance

evidence/deployment-20261113 contains sanitized backup, restore, baseline origin,
connector and restart/resource receipts plus3 deployment-boundary tests with3
subtests. Baseline resource inspection confirmed all three new services healthy and
four connector HA connections. These are software integration results, not clinical
effectiveness or a high-availability certification.

Final parent-integrated public acceptance PASS: evidence/triadic-release/public-final/browser-acceptance.json and access-boundary.json. Actual Chrome saved a synthetic document, called real Typhoon once, edited v2, approved, committed and reloaded the unchanged result. The separate read-only receipt public-workflow-readback.json confirms exact revision/approval/result hashes, one attempt/result and six bound audit records.

Sources: [Docker host networking](https://docs.docker.com/engine/network/drivers/host/)
and [Cloudflare origin/Access parameters](https://developers.cloudflare.com/tunnel/reference/origin-parameters/).

## Dedicated synthetic test account

The owner explicitly authorized a separate test01 account on the server. It has only the clinician membership at facility-demo and care assignment for patient-001. It does not have identity administration, operations, finance or wildcard permissions. Existing users and the global account-creation password policy were not changed. Provisioning used the existing Argon2 helper and an audit event, with no plaintext password saved in source/evidence. Actual login, document/AI/human-review permissions, admin403 and other-patient404 were verified; the probe session was logged out. See test-account-provisioning.json.

## Activated triadic candidate

The current-working-source snapshot SHA256 is
778ba97bf46f714b0b9290555549a6aeab09d5228e279204d28a53a1f8d8f7d4.
Its201 source files were verified before building the immutable image
his-poc-server:triadic-778ba97bf46f. Runtime image ID:
sha256:6144c7744b6976c8f0c142486acc4baaa283f0515f1d36c3a951337e53773935.

A fresh active-server database/files backup was taken immediately before replacing
only the app container. No database restore, seed, account reset or connector restart
occurred. All178 prior session records and the dedicated test account were unchanged;
the old committed live result and file checksum remained present.

After activation,48 runtime source hashes and21 built assets matched the current
Windows checkout/build exactly. The three new services were healthy; app18080,
PostgreSQL15432, Ollama11434 and connector metrics20331 all bound only127.0.0.1.
Connector retained four HA connections. See final-deployment-verification.json and
final-resource-verification.json under evidence/deployment-20261113.

The parent integrator owns final external browser and real-model workflow evidence.
This activation receipt does not replace that acceptance.
