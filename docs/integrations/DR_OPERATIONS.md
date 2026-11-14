# CareBalance DR operations

The named runtime is `/home/chaw/his-poc` on dr-train. DR is a separate manual
review service and database. The original DR project, model services, LabClear
customer application, Cloudflare Access policy and DNS are outside this update.
See [release state](DR_RELEASE_20261114.md) before taking operational action.

## Configuration

The tracked [Compose overlay](../../deploy/dr-train/compose.dr.json) and
[empty environment template](../../deploy/dr-train/dr.env.example) contain no
credentials. Actual `var/dr.env` stays server-only with mode0600. Registry and
manifest use a mode0700 directory owned by UID10001, with mode0600 files.
Frontend assets are an exact reviewed main build, mounted read-only; the licensed
DR source and generated bundle are not published in the HIS repository.

Every operational Compose command must layer all three environment files and
overlays in this order. Base-only startup selects an obsolete image.

```sh
docker compose --project-directory /home/chaw/his-poc \
  --env-file /home/chaw/his-poc/var/server.env \
  --env-file /home/chaw/his-poc/var/labclear.env \
  --env-file /home/chaw/his-poc/var/dr.env \
  -f /home/chaw/his-poc/deploy/dr-train/compose.json \
  -f /home/chaw/his-poc/deploy/dr-train/compose.labclear.json \
  -f /home/chaw/his-poc/deploy/dr-train/compose.dr.json ps
```

HIS18080, LabClear18090, DR18190 and PostgreSQL15432/15433/15435 bind loopback
only. The existing tunnel supplies the protected `https://his.ai-cie.com` route.
Do not create a new public DR hostname or expose a database/model port.

## Release and recovery

Required order: verify immutable image/source/asset identities and private
browser acceptance; take a consistent HIS dump and separately hash file bytes;
actually restore to a new isolated database and directory; select the rehearsed
03/04-compatible app; explicitly migrate04; start the candidate with an empty
registry; create authored synthetic acquisitions through normal typed APIs;
seal their consent/source set; prepare only the dedicated DR database and fixed
receiver; then verify old records, accounts, sessions, files, services and real
AI results before public browser acceptance. Startup never seeds or migrates.

Private phase receipts and original configuration copies remain under
`var/dr-production-<release-id>` on the server. They can contain credentials or
session material and must not be copied into public evidence. A RUNNING phase or
lost response requires read-only inspection of its actual process, job, database
revision and request ledger. Do not replay it with a different key.

After migration04, recovery replaces only the app with the rehearsed compatible
image. Retain the database, newer writes and receiver evidence. Do not downgrade,
restore an old dump over production, reset a source set or discard an unknown
remote command. An unavailable DR service must not stop core HIS readiness.

## User and data boundaries

Open a released CFP record under Radiology and choose **DR screening**. Select
only registered sources for the current patient and visit, record explicit
transfer consent, review image quality and reconfirm image context, then prepare
a report. Returning to CareBalance retains the exact source record. The HIS
review task stays open until its own authorized workflow changes it.

The test account may prepare an unsigned draft. A generic clinician role does
not grant DR grade confirmation or signing. Historical signatures and current
review freshness remain separate. No retinal model runs in this receiver.

The ten owner-renamed MMRDR images remain held for laterality metadata. They are
not deployment fixtures. See [source intake](PUBLIC_CFP_INTAKE.md).
