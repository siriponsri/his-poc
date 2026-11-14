# AI workspace frontend candidate

Prepared 2026-11-14 in managed worktree `care-ai-ui/his-poc`, branch `feat/ai-workspace-3d`, based on `f9fd47f9b3e6b5cc37834a2ac695ea5100da258c`. Frontend changes only; no provider/server/model calls, database migration, push or deployment was performed by this task.

## Staff journey

1. Home reads authoritative assistant configuration and available profiles. Disabled/unavailable profiles preserve the existing Work queue. Existing patient record, D37, LabClear and DR screens retain their routes.
2. Choose the preparation profile available to the current account. Prepare one eligible visit or explicitly prepare up to six eligible visits. Keep-prepared watches are off by default.
3. Read the persisted execution/review state. Queued, waiting for capacity, failed, unavailable and stale results remain distinct. Reads and rendering never submit inference requests.
4. Review source-backed facts, work gaps and the draft in the wide reading area. Primary citations use supplied titles or friendly source kinds. Exact aliases, fields, quotes, hashes and provider details remain in disclosures. Open the existing wide Patient record panel when needed.
5. Optionally edit the first draft. An edit retains its displayed source/revision snapshot; refreshed revisions disable apply until the edit is discarded and current data is read. A single explicit Use draft/Create selected follow-ups action sends the expected revision/version/hash/source digest and selected server candidate IDs. Saved effects can open their ordinary source-domain workflow using actual returned identifiers.
6. Explicitly opt into a bounded 30-minute watch or pause the exact active watch. The UI reports supplied expiry and automatic-run counts. Unknown mutation responses retain the exact body/key and block context switching until the same request is recovered. Malformed/foreign receipts do not confirm success.

The server supplies profile availability, sources, allowed candidates and permissions. Records readiness displays only supplied metadata and has no invented clinical text. Laboratory preparation does not order, interpret thresholds, sign or release results.

## Optional 3D

Operations is off by default and lazy loads its own module and Three scene. It is one independently authored six-station hospital/agent-office illustration. It does not represent a real building or staff positions. All counts/run states come from the scoped Operations DTO; unavailable counts stay unavailable. Rooms open the same profile worklist; agent markers select their actual run, with a scoped read if absent from the current list.

OrbitControls and Raycaster provide orbit/zoom/picking. Identical room/run actions remain in keyboard-accessible DOM lists. Reduced-motion is respected through a static, render-on-demand scene, without auto-rotation or simulated activity. Resize/controls/data changes trigger rendering; unchanged timestamp refreshes do not reconstruct the scene. Cleanup disposes controls, geometry, materials, textures, renderer/context, handlers, observers and animation frames. Camera position survives actual data refreshes.

Reference-only research: Hermes3D `beb76292747b816ef317aa6f9a3992e0014f81d9` README, MIT license and `src/features/retro-office/RetroOffice3D.tsx`; 3d-force-graph `cf4c8d7f1e2173763fb221c8575dc7139d11881e` README, MIT license and click-to-focus example. The useful spatial/picking approach was retained; full office simulation and a separate force graph were excluded to keep staff work primary. No source/assets from either repository were copied. Runtime dependency is only direct Three 0.187.0; matching types and their transitive dependencies are development-only. Runtime MIT notice is bundled.

## Evidence

| Check | Status | Evidence |
|---|---|---|
| Baseline units, 31 | PASS | `unit.log` |
| Full mounted suite, 152 (139 baseline + 13 new) | PASS | `components-polished.log` |
| TypeScript + production build | PASS | `build-polished.log` (`tsc --noEmit` is part of build) |
| Legacy audit probes, 3 / reproduced defects 0 | PASS, bounded probe only | `audit-regression.log` |
| Isolated browser, authored fixtures only | PASS | `browser-fixture-result.json`, three `*-fixture.png` files |
| Actual API / persisted worker / dr-train inference | NOT_RUN | Parent integration acceptance remains required |
| Public Cloudflare URL / clinical validation / throughput | NOT_RUN | Parent release acceptance remains required |
| npm vulnerability audit | FAIL: existing low dev dependency advisory | `npm-audit.json.log` |

Browser checks intercepted all API requests with explicitly authored synthetic DTOs and aborted other external origins. They verified real WebGL initialization, real Raycaster room selection, zero POSTs, zero page errors, no scene download before selecting Operations, and no document overflow at 390px. This is not real model, backend persistence, clinical accuracy or performance evidence. Screenshots were rendered and visually inspected at desktop/mobile sizes. The optional Three chunk is ~570 kB minified/~142 kB gzip and retains Vite's size warning; the ordinary page does not fetch it.

Retained earlier failures: first typecheck found optional Home callback/unknown ReactNode typing and was corrected; `components.log` retains an invalid fallback `<p><details>` warning corrected to a `<div>`; `components-final.log` retains a navigation test failure after the intentional Work queue→Workspace entry rename, fixed by updating that test label. Final 152 mounted checks pass with no invalid-nesting warnings. Browser harness attempts initially lacked sandbox `URL` and could not read a worktree filename outside its allowed roots; the successful run used the same saved function as inline code, with screenshot bytes saved only to this worktree. No failed model call is hidden.

PowerShell Tee logs may format npm's stderr notices as `NativeCommandError`; actual exit codes/test totals are recorded in `checks.json`. No audit fix or unrelated dependency upgrade was performed. `source-hashes.json` identifies the reviewed source files.

Harness notes: the ray-picking test independently imports the raw Three module to project a known room coordinate; Vite reports a multiple-Three-instance warning for that test-only projection import. Production code imports a single pinned Three package. An initial manifest command found `Get-FileHash` unavailable in the shell; the final manifest uses .NET SHA256 over the actual source bytes instead.
