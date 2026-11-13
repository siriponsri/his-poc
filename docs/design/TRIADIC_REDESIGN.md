# Triadic workbench redesign

Base:39f788fa956e09bc4a87f200b63aef92cfcd8698.
Date:13 November2026. Data:authored synthetic only.

## Scope and method

The user explicitly requested a full UX/UI redesign, no-slop-ui guidance, Hallmark examples and the exact anchors #1C4286 / #861C42 / #42861C. The existing application, backend and live dr-train wiring were the material. This was an app-screen run: no marketing hero, theme lottery, stock imagery, fake numbers or decorative chart.

Read local interface-design and design-system skills, no-slop-ui/SKILL.md plus banned-patterns, and Hallmark redesign/app-screen guidance. The product already supplied audience, task and material, so no additional design interview was necessary. Files edited were existing apps/web/src components/styles plus focused regression tests; no route or file was deleted. DESIGN.md records the locked system.

## What changed

- Home's parallel framed summaries became one flat task register with search, actual status filtering and exact task/context destinations. Workload counts moved to a secondary disclosure. Existing counts, history, directory and routes remain available.
- Shared record screens use adjoining list/detail work surfaces instead of independent cards; forms, state transitions, permissions and pending-operation recovery remain wired.
- D37 compact intake leads into source-left / findings-and-human-review-right. Proposal selection, binding identifiers, model metadata, run history and results use progressive disclosure.
- Removed the misleading six-step ribbon. Rejected and committed states are expressed by their actual status and available actions.
- Unknown or mismatched proposal subject metadata cannot be actionable under another patient/encounter. Authorized history with no global context is readable but requires matching global context before any review mutation.
- Corrected same-patient/different-encounter task navigation and browser-history restoration.
- Mobile drawer traps focus, makes the underlying main inert and restores trigger focus after inert removal. The real-browser check found and repaired a timer ordering problem missed by jsdom.
- Replaced decorative status dots with meaningful icons. Controls use readable boundaries and a direct focus ring; triadic anchors are semantic rather than page decoration.

## Executed checks

| Evidence | Result and scope |
|---|---|
| evidence/triadic-ui/release-checks |25 unit/69 component, audit, TypeScript and production build PASS before the final Escape timing repair |
| evidence/triadic-ui/final-freeze |69 component, TypeScript and production build PASS after that repair; source stayed unchanged during the run |
| evidence/triadic-ui/confirmation/execution.json |13 actual Chromium observations PASS, desktop1440/tablet1024/mobile390. Waited for8 real Home rows; five persisted model findings and11205ms historic provenance read back under explicit patient001/encounter001. Drawer focus/inert/Escape verified. No inference/domain writes. |
| evidence/triadic-ui/hallmark-final-render.txt |Hallmark static + login render:0 FAIL,0 REFLEX,2 WARN. Five login captures across375/1280/1440/1920 widths; authenticated workspaces checked separately. |
| evidence/triadic-ui/checks |Initial run retained: create-label presentation change broke existing control discovery. Original ＋ เพิ่ม copy was restored, not the assertions weakened. |

Six new behavioral regressions cover proposal subject mismatch/unknown metadata, read-only unscoped history, context changes clearing actionable proposals, exact same-patient task/encounter plus history navigation, real Home filters and mobile focus containment. Existing HTTP fixture DTOs gained their actual contract identities; existing capability/assertion checks remain.

The two Hallmark F7 warnings identify consistent input/button/disclosure recipes in the legacy shared stylesheet. They are retained deliberately for a familiar operational control system, not used to create repetitive content cards. Rendered field-edge contrast was repaired by strengthening the shared border token. Hallmark's optional isolated puppeteer-core25.17.0 lives under ignored var/hallmark-runtime; it is not an application dependency or global installation.

The first preview's desktop Home screenshot showed a loading skeleton despite an overall navigation pass. It is retained as loading-state evidence only, not full-state acceptance. The final confirmation explicitly waits for populated task rows. Actual browser inspection found Escape focus could be attempted while main was still inert; deferring it until the state update and waiting for restored focus passed in both real browser and components.

## Source provenance

- [no-slop-ui](https://github.com/LeoStehlik/no-slop-ui), commit822198acad493618190f3f0527713a386c8a70c3. MIT, copyright2026 Leo Stehlik; LICENSE inspected.
- [Hallmark](https://github.com/nutlope/hallmark), commit04977e15f3dfd6ee4b74c887dac3eb52665d6c92. MIT, copyright2026 Hallmark contributors; LICENSE inspected.

The repositories were cloned to ignored var/references for consultation and lint execution. No competitor code, photos, logos, illustrations or templates were imported into the application. The Hallmark stamp records the method, not a claim that every existing workflow was authored by that project.

## Handoff

Frontend source is frozen. Root owns independent cold review, deployment packaging, server image/runtime binding and external URL acceptance. Local preview evidence is not public deployment or a new clinical/model benchmark. Source snapshots and raw logs distinguish preliminary, repaired and final runs. Existing backend permissions, CSRF, immutable approvals, idempotency and failure retention remain authoritative.
