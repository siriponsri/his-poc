# README visuals and provenance

These three visuals explain CareBalance's implemented workflow and retained
synthetic acceptance. They were authored for this repository from the inspected
`dbdfce7cb167e01d542e6bfbeae88e010d368ba3` baseline. No third-party diagram code,
template, icon set or external media was copied. The existing approved CareBalance
wordmark remains unchanged.

## Artifacts and editing

| Visual | Editable export | Rendered preview | Question answered |
| --- | --- | --- | --- |
| Deployed logical architecture | [SVG](branding/readme-architecture.svg) | [PNG](branding/readme-architecture.png) | How do Access, the HIS origin, persistence, AI and specialist services connect? |
| Source-bound workflow | [SVG](branding/readme-workflow.svg) | [PNG](branding/readme-workflow.png) | What happens between choosing a visit and saving the reviewed work? |
| Six-call observation | [SVG](branding/readme-trial.svg) | [PNG](branding/readme-trial.png) | What durations and input coverage were actually recorded? |

The editable generator is [render_readme_visuals.py](../scripts/render_readme_visuals.py).
SVG generation and validation use the Python standard library. Optional PNG
rendering uses an already installed CairoSVG package. No package installation,
external asset request, database access or model call occurs in the generator.

```powershell
python scripts/render_readme_visuals.py
python scripts/render_readme_visuals.py --check
# Optional, in an environment where CairoSVG is already available:
python scripts/render_readme_visuals.py --png
```

The diagrams use the existing blue `#1C4286`, burgundy `#861C42` and green
`#42861C` palette on neutral surfaces. SVGs include a descriptive `<title>` and
`<desc>`, readable text, and no scripts, external font files or linked assets.
PNG previews are exported at the SVG viewBox dimensions. Color accompanies
text and line geometry rather than being the only indication of meaning.

## Source map

Arrows in the architecture diagram describe primary logical flow; they are not
an exhaustive dependency map, physical network diagram or availability claim.

| Node or relationship | Inspected source |
| --- | --- |
| Staff browser → Access/Tunnel → protected HIS origin | [Deployment guide](DEPLOY_DR_TRAIN.md), [architecture](ARCHITECTURE.md), [deployment readback](../evidence/ai-driven-root-20261114/deployment-readback.json) |
| React workspace and FastAPI `/api/v2` share an origin | [Application factory](../backend/app/main.py), [architecture](ARCHITECTURE.md) |
| Server session, CSRF, facility, role and patient care scope | [Authentication](../backend/app/auth.py), [assistant API](../backend/app/assistant_api.py), [actual role checks](../evidence/ai-driven-root-20261114/application-acceptance.json) |
| PostgreSQL stores queue, versions, effects and audit | [Assistant models](../backend/app/models_assistant.py), [shared models](../backend/app/models.py), [source contract](AI_DRIVEN_CONTRACT_V1.md) |
| File storage retains source bytes and checksums | [Architecture](ARCHITECTURE.md), [operations](OPERATIONS_FULLSYSTEM.md) |
| Durable queue/watch → separate worker → private Typhoon | [Worker](../backend/app/assistant_worker.py), [provider](../backend/app/assistant_provider.py), [actual runtime witness](../evidence/ai-driven-root-20261114/assistant-runtime-readback.json) |
| Current identity is revalidated; inference runs without an open DB transaction | [Worker](../backend/app/assistant_worker.py), [source-bound contract](AI_DRIVEN_CONTRACT_V1.md) |
| HIS → isolated LabClear and DR services through scoped gateways | [LabClear gateway](../backend/app/integrations.py), [DR gateway](../backend/app/dr_gateway.py), [integration checkpoint](integrations/VALIDATION_CHECKPOINT_20261114.md) |
| Human review → immutable edited revision → selected effects once | [Effect service](../backend/app/assistant_effects.py), [actual application acceptance](../evidence/ai-driven-root-20261114/application-acceptance.json) |
| Opt-in source-change watch, limits and feedback suppression | [Worker](../backend/app/assistant_worker.py), [collectors](../backend/app/assistant_collectors.py), [source contract](AI_DRIVEN_CONTRACT_V1.md) |

The separate existing document-completeness provider route is mentioned in the
architecture footer rather than expanded into a second model pipeline. Backups,
all domain modules, legacy isolated adapters and detailed connector retries are
omitted to preserve the diagram's question and reading order.

## Chart definition

Input: [application-acceptance.json](../evidence/ai-driven-root-20261114/application-acceptance.json),
SHA256 `c7622c451e5aec19c5dc070f3a7e91e691935def421b11eea75b0e60dc18d02c`.
Its six records were captured on 14 November 2026 UTC, which is 15 November in
Thailand. The original and corrected nursing sources are distinct calls. The
original nursing output was preserved without applying it.

| Mark | Definition |
| --- | --- |
| Blue timing bar | Recorded `elapsed_ms / 1000` for the provider boundary |
| Dark timing dot | Recorded `queue_to_completion_seconds`, from queue-record creation to completion |
| Connector between bar and dot | Additional end-to-end elapsed time; it is not labeled as a separately measured queue stage |
| Blue coverage segment | `included_sources` |
| Pale coverage segment | `omitted_sources`; the whole bar is `eligible_sources` |
| Coverage label | Exact included / eligible count; all coverage bars share a 0–12 source scale |

Durations share a zero-based 0–80 second scale and are displayed to one decimal
place. The SVG description retains the three-decimal timing observations for
screen-reader users. No mean, percentile, speedup, target, trend or percentage of
staff time saved is inferred from this small authored-data trial. Source counts
are not equivalent to clinical completeness. Monetary cost remains unmeasured.

## Verification

Executed on the documentation branch:

- **PASS:** standard-library SVG generation, XML parsing, unique SVG identifiers,
  accessible title/description and absence of scripts or external references.
- **PASS:** `python scripts/render_readme_visuals.py --png`, using the installed
  global Python 3.12 and CairoSVG renderer. All three PNG exports were opened and
  visually inspected. Architecture label placement was adjusted and the final
  export inspected again.
- **PASS:** `python scripts/render_readme_visuals.py --check` confirms the checked-in
  SVG bytes match the generator and retained evidence.
- **PASS:** local Markdown/HTML links and image paths in the README and this guide
  resolve inside the repository. External endpoints were not fetched.
- **PASS:** `git diff --check` for the owned documentation change.
- **NOT_RUN:** application, PostgreSQL, model and deployment tests for this
  documentation-only change. Existing runtime claims cite their dated evidence;
  none are promoted from a diagram or screenshot.

GitHub's full rendered Markdown page was not inspected by this authoring task.
The SVG and PNG assets were inspected directly. Publication and any subsequent
Admin-console claims remain the integrating agent's responsibility.

Administration now links to its separately verified protected release and native desktop screenshot. Product direction remains proposed work. The three generated visual assets and generator are unchanged by these additions; current link checks are recorded at release. See [Admin release](ADMIN_RELEASE_20261115.md) for deployment, account and browser evidence.
