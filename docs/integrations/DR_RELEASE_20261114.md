# CareBalance DR release checkpoint

## Current manual-quality checkpoint

Long goal ACTIVE. The current HIS and receiver images are running only in the
private Linux shadow. Production remains the existing HIS5328/LabClearc194
deployment on migration03 with9 inference rows at the last preservation check.
Public DR activation/browser acceptance, fresh production backup/isolated
restore and controlled main integration/rebuild remain open.

| Gate | Current executed result | Evidence |
| --- | --- | --- |
| HIS gateway, provenance and actual two-process HTTP |77 passed on PG18.6; zero skips | [Backend qualification](../../evidence/integrations/dr-manual-qualified-20261114/backend-qualification.json) |
| Receiver manual-quality and clinical guards |37 passed; separate independent2 passed | Same qualification and receiver.xml/independent.xml |
| Complete DR frontend before the final small UX refinement |514 passed; typecheck/build; source and191 native-backend files unchanged | Derivative frontend/evidence/carebalance-manual-quality-qualified-20261114/checks.json |
| Final scoped frontend UX refinement |RUNNING at this checkpoint; do not infer a pass from the prior514 run | Derivative frontend/evidence/carebalance-manual-ux-qualified-20261114/checks.json when complete |
| HIS frontend |25 unit/135 component/3 audit cases and build passed | [Receipt](../../evidence/integrations/dr-manual-ui-20261114/checks.json) |
| Private Linux upgrade |PASS; all three databases/source files unchanged; no migration, seed or backfill | Private operator receipt manual-quality-upgrade-20261114-v1-20261114T103543Z.json |
| Private actual browser |Coordinator-observed draft/reload, permission, mobile390 and exact-return checks; final UX bundle recheck still open | [Browser checkpoint](DR_BROWSER_CHECKPOINT_20261114.md) |

Current immutable software images:

- HIS `his-poc-server:workspace-074aa8f8a0b2`, image
  `sha256:a30f5e9d1e9284942343098423b0bfe56e27c91325d84fb68b86b3d4c22159f0`;
  245 source inputs. [Build receipt](../../evidence/integrations/deployment-dr-manual-20261114/candidate-build.json).
- DR `his-poc-dr:source-05476e8f5ebb`, image
  `sha256:2891650421e89546783d9c3a268dbdc8f6fcef3ebbe84500163be6f6c894d2e5`;
  200 runtime inputs, including191 unchanged inherited backend files. Its source
  package and private frontend bundle stay separate from public HIS Git.
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
