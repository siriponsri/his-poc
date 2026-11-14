# Owner-provided public CFP intake

Status: source inventory inspected; clinical source registration and transfer NOT_RUN.

The owner authorized using the ten JPEG files in the local image-cfp folder,
identified their source as MMRDR, and explicitly confirmed on 2026-11-14 that
the IDRiD_01.jpg through IDRiD_10.jpg filenames were assigned by the owner.
Those renamed filenames are not evidence of a different dataset.

## Attribution and evidence

MMRDR version 2, DOI [10.6084/m9.figshare.29423747.v2](https://doi.org/10.6084/m9.figshare.29423747.v2).
The [official Figshare API](https://api.figshare.com/v2/articles/29423747)
returned HTTP 200 and declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Use the exact author list in the retained upstream metadata when producing the
final attribution receipt. Owner-confirmed membership and independently
verified upstream metadata are separate evidence fields. Exact upstream-file
hash matching has not been performed.

Version2 is the independently retrieved upstream metadata version. The owner's
local-file membership is attested; exact upstream image/version matching remains
unverified. The owner explicitly chose to keep these images pending laterality
instead of assigning eyes or patient pairs without metadata.

The upstream README uses tr/ts filenames and FP.csv for eye metadata:
lr=0 is left, lr=1 is right. No rename mapping or per-file eye metadata has
been supplied. Do not infer laterality, capture time, grade, patient grouping,
or same-patient pairs from the renamed files or their appearance. Missing
clinical metadata must not be replaced by invented annotations.

All ten local files decode as JPEG, 4288 by 2848 pixels. Each is below the
existing 1 MiB image limit. Preserve the original bytes and filenames; retain
their SHA-256 inventory. Do not recompress, rewrite EXIF, relabel these images
as synthetic, publish the bytes to Git, or invoke a model as part of intake.

## Authorized public-source extension

This owner-authorized extension supersedes only the synthetic-only origin and
PNG-only media restriction of the new CareBalance bridge. It does not change
the original DR repository, native clinical workflow, identity confirmation,
grade/signing credentials, quality gating, original-image geometry, or model
policy. Keep the existing synthetic v1 snapshots and consent receipts valid.

Allow PUBLIC and SYNTHETIC origins; allow exact image/jpeg and image/png bytes.
The receiver must verify declared media against signature, full decoder
validation, dimensions, length and SHA-256 before sealing a complete source
set. PUBLIC source registration requires an immutable, server-recorded dataset
provenance receipt, including license/attribution, membership evidence basis,
owner rename statement, and explicit per-source laterality evidence. A browser
upload or checkbox does not establish public provenance or eye identity.

Public consent wording v2 describes public dataset/manual review, exact image
set and destination, and grants no inference permission. Do not accept old
synthetic-only wording for a PUBLIC source set. Unknown eye metadata prevents
clinical binding of that image; it does not prevent implementing or testing
the general public-source path using isolated fixtures.

Before activation, qualify sender, receiver, schema and UI together on isolated
PostgreSQL and actual signed HTTP. Rebuild source-only receiver artifacts and
frontend manifests; prior synthetic-only image/test receipts are historical.
