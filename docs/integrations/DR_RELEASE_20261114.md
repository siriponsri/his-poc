# CareBalance DR release checkpoint

## Current manual-quality checkpoint

Long goal ACTIVE. HIS main `ac63879e166c41c65b96f75a3ed22408e97bc11f`
was merged and pushed. The separate derivative's authoritative local main is
`6359e598cd594bd23a6e791ab5e90699268ef80b`, without a remote; its191 inherited
backend files remain unchanged. The current images and final main frontend run
only in the private Linux shadow. Production remains HIS5328/LabClearc194 on
migration03, preserving all9 stored inference results, including the3 selected
results. Fresh production backup and actual isolated restore passed at
2026-11-14T11:07:21Z:112 tables and1 file, with no production migration/seed.
Deployment materials are being prepared/diagnosed; no completed materials phase
or public DR activation/browser acceptance is claimed.

| Gate | Current executed result | Evidence |
| --- | --- | --- |
| HIS gateway, provenance and actual two-process HTTP |77 passed on main, PG18.6; zero skips | [Main XML](../../evidence/integrations/dr-main-qualified-20261114/his.xml) |
| Receiver manual-quality and clinical guards |37 passed on main; prior separate independent2 passed | [Main receiver XML](../../evidence/integrations/dr-main-qualified-20261114/receiver.xml) and [independent qualification](../../evidence/integrations/dr-manual-qualified-20261114/backend-qualification.json) |
| Complete final DR frontend branch |516 passed; typecheck/build; no source/native-backend drift | Derivative frontend/evidence/carebalance-manual-ux-qualified-20261114/checks.json |
| Authoritative derivative main frontend |70 focused tests, typecheck and main rebuild passed;191 native backend unchanged | [Main frontend receipt](../../evidence/integrations/dr-main-qualified-20261114/dr-main-frontend.json) |
| HIS frontend |25 unit/135 component/3 audit cases and build passed | [Receipt](../../evidence/integrations/dr-manual-ui-20261114/checks.json) |
| Private Linux upgrade |PASS; all three databases/source files unchanged; no migration, seed or backfill | Private operator receipt manual-quality-upgrade-20261114-v1-20261114T103543Z.json |
| Final main static refresh |All10 authenticated assets match;3 databases/files, registry bytes and other5 containers preserved | [Static receipt](../../evidence/integrations/dr-main-qualified-20261114/shadow-static.json) |
| Private actual browser |Final main bundle save/loading, stale-message, unsigned copy, reload and mobile390 checks passed | [Final browser receipt](../../evidence/integrations/dr-main-qualified-20261114/private-browser-final.json) |
| Private persisted readback |Unsigned draft, exact notes, original D11v6/source bytes, open review task,0 inference/grants/pending writes | [Read-only DB receipt](../../evidence/integrations/dr-main-qualified-20261114/prior-browser-database-readback.json) |

Current immutable software images:

- HIS `his-poc-server:workspace-074aa8f8a0b2`, image
  `sha256:a30f5e9d1e9284942343098423b0bfe56e27c91325d84fb68b86b3d4c22159f0`;
  245 source inputs. [Build receipt](../../evidence/integrations/deployment-dr-manual-20261114/candidate-build.json).
- DR `his-poc-dr:source-05476e8f5ebb`, image
  `sha256:2891650421e89546783d9c3a268dbdc8f6fcef3ebbe84500163be6f6c894d2e5`;
  200 runtime inputs, including191 unchanged inherited backend files. Its source
  package and private frontend bundle stay separate from public HIS Git.
- Final derivative main dist manifest:
  `7c7628f9c64550650e704a8ed06cdf56d2d38f81bb7bbe06f03fb42c1e6b4aaf`;
  10 protected assets, including `assets/index-BkzaUflX.js`.
- Compatibility rollback `his-poc-server:rollback-0004-2c88b48dca31`, image
  `sha256:e6e336a6f9515710dbe3c37a3e0af80daed57f9e0788e65d8553fdac58f966d0`;
  same-DB old-LabClear-UI rehearsal passed before restoring the new candidate.

The browser exposed a real manual-quality dead end for NOT_EVALUATED images.
The bound adapter now offers explicit quality decisions, preserves quality
through image confirmation, requires verified manual-quality evidence before
grade/signing and invalidates a prior confirmation witness after a later quality
review. Native backend bytes and the wire protocol remain unchanged. The
backend qualification's earlier frontend RUNNING/runtime NOT_RUN values are
historical fields, superseded only by the separate later receipts above.

Ten owner-renamed MMRDR images remain HELD_FOR_LATERALITY, untouched and unpaired.
No new image inference or DR grade/signing grant was made. A public-classified
authored JPEG fixture proves transport/guards, not MMRDR clinical annotations.

## Earlier PUBLIC/JPEG qualification and build history

The remainder records the preceding candidate. Its counts, image tags and
unfinished runtime statements are historical, superseded by the current
checkpoint above; retain the original receipts and failed attempts.

Long goal ACTIVE. Software qualification and builds pass; new private Linux
rehearsal is ongoing. Public DR activation/browser acceptance remain NOT_RUN.
Existing public LabClear remains on qualified migration03.

HIS branch feat/carebalance-dr-bridge, base0c003e7. Separate derivative branch
feat/carebalance-his-bridge, basea9932be. Original DR source/Git/runtime are
untouched; all191 inherited derivative backend files match baseline. No DR
source repository has been published.

| Gate | Executed result | Evidence |
| --- | --- | --- |
| HIS gateway/provenance/sender/actual two-process HTTP |77 passed, PG18.6, zero skips | [Qualification](../../evidence/integrations/dr-public-qualified-20261114/qualification.json) |
| Receiver PG/clinical/source/restart |35 passed | [XML](../../evidence/integrations/dr-public-qualified-20261114/receiver-public-35.xml) |
| DR frontend |513 passed, typecheck/build passed, source/native drift zero | Derivative frontend/evidence/carebalance-bound-public-20261114/checks.json |
| HIS frontend |25 unit/135 component/3 audit cases/build passed | [Receipt](../../evidence/integrations/dr-public-launcher-20261114/checks.json) |
| Independent provenance review |8 origin and5 grouping probes passed | Console-only review recorded in qualification |
| LabClear regression |44 tests and62 subtests passed | [XML](../../evidence/integrations/dr-public-qualified-20261114/labclear-regression.xml) |
| Alembic |Upgrade/check passed,121 tables, revision0004 | [Schema](../../evidence/integrations/dr-public-qualified-20261114/schema-check.json) |

PUBLIC-classified authored JPEG fixtures test transport and guards, not actual
MMRDR annotations or clinical effectiveness. The ten owner-renamed files are
held pending eye metadata per the owner's explicit choice. See [intake](PUBLIC_CFP_INTAKE.md)
and [hold receipt](../../evidence/integrations/public-cfp-intake-20261114/owner-laterality-hold.json).

Reports use the real nested receipt.snapshot and compare displayed stored
report/revision before claiming current review. Reads retain pending write
fences. Late-save edits remain dirty. Unknown transfers can be closed/reopened
without discarding the command; imported pending workspaces remain readable.

PUBLIC/SYNTHETIC remain distinct. JPEG/PNG retain exact bytes/geometry, with
signature, MIME, full decode, size and hash checks. Immutable public/eye/grouping
evidence enters source snapshot v2; PUBLIC requires consent v2. Isolated images
cannot form pairs. Returned origin/modality cannot contradict sealed sources.
No new signing/grade grant or model call was made.

Built, not activated:

- HIS his-poc-server:workspace-d72838615e3d, image
  e53525f17f40416fbed8437b7144a28668f1320b080433bd83237e99a5abc95e,
  245 source inputs. [Build](../../evidence/integrations/deployment-dr-public-20261114/candidate-build.json).
- DR his-poc-dr:source-90d4b78ec73f, image
  9b1d1f105f61f750afa8ff1b84354c96e907429cf4729a560eb79a5ad969c93c,
  202 package members, no images/models/private data. Kept separate from HIS Git.
- LC UI rollback his-poc-server:rollback-0004-2c88b48dca31, image
  e6e336a6f9515710dbe3c37a3e0af80daed57f9e0788e65d8553fdac58f966d0.
  Only readiness accepts actual03/04. Same-DB rehearsal remains required.
  Initial image-ID-as-registry-name build failed before activation; retained log
  and corrected local-tag/exact-ID build are separate evidence.

Remaining: private Linux workflow/rollback, fresh production backup/isolated
restore, explicit migration/app-only activation/new DR DB, protected public
browser/persistence/preservation, controlled main release and final handoff.
test01 has no verified DR grade/signing grant. Original DR remains untouched;
the licensed derivative remains local/separate.
