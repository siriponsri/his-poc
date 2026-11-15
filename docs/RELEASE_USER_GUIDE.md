# Illustrated User Guide release

Status: **DEPLOYED_AND_GUIDE_ACCEPTED**. Open [his.ai-cie.com/guide](https://his.ai-cie.com/guide)
after the existing Cloudflare Access gate. Runtime source `65c5bc517b0b5905355ebc2a161c93635a9a7c97`,
image `sha256:92166e35ebf84c8dc3c6aff480a1d83d6e261f7ad017353af5300f6256323ab9`, schema 0005. No migration or seed ran.

## Reader experience

The guide opens from sign-in, the top-bar shortcut or sidebar. It provides 16
task-based chapters with 101 steps, plus 38 domain references with 152 working steps.
Chapters cover access, queues, the wide patient record, registration/visits,
immutable documents, document-completeness review, four AI preparation profiles,
team tasks/handover, orders/medication, LabClear, DR, finance, supply/operations,
portal/reporting, administration and recovery.

Search includes instructions, troubleshooting and human role labels. Optional
role filtering never changes account permissions. Chapter/domain query links
can be shared; the mobile contents action returns focus to search. Each topic
states prerequisites, ordered steps, completion checks and recovery paths.

Eleven exact synthetic screenshots illustrate the workflows. Ten have explicit
Play/Pause and previous/next explanations with pointer highlights. Playback is
paused initially; reduced-motion readers retain manual steps and a full text
transcript. Images open in a labeled modal with original-size keyboard scrolling,
focus containment, Escape/close and focus restoration.

The screenshots are illustrations, not live controls. The DR and new LabClear
captures show pretransfer review, with no consent/send action performed during
capture. A separately dated retained LabClear image illustrates a confirmed
review; it does not claim a new confirmation. No held MMRDR image was sent or
assigned laterality. [Exact media sources and hashes](USER_GUIDE_MEDIA.json).

## Qualification

| Layer | Result | Scope |
| --- | --- | --- |
| Frontend unit | PASS 31 | Existing unit suite |
| Mounted frontend | PASS 195 | Prior 171 plus 20 guide and 4 guide-shell cases |
| Guide data/provenance | PASS | 16 chapters, 38 canonical domain names/IDs, 11 referenced image hashes/alt text and bounded tour rectangles |
| Typecheck/build | PASS | 32 dist assets; guide lesson bundle loaded lazily; existing main/optional 3D chunk warning retained |
| Independent review | PASS | Workflow/content/role boundaries, captions, route privacy, keyboard/motion and release controls |
| Native local reading | PASS subset | Search/navigation, actual timed advance, original-size Tab reachability and ArrowRight scrolling 0→40; mobile 390 document 380 and return-to-search focus |
| Protected public reading | PASS subset | See [actual browser acceptance](../evidence/user-guide-20261115/browser-acceptance.json) |
| Immutable server/static | PASS | 348 runtime inputs and 32 assets as UID/GID 10001, all backend/auth/AI/dependency bytes unchanged |
| Runtime/preservation | PASS | Fresh foreground worker identity/engine pins, schema 0005, exact retained clinical/AI/LabClear/DR rows/files; normal authentication deltas reported separately |

The local Vite preview had no API backend; its ordinary auth/me proxy refusal was
expected and static help remained readable. It was not a production/API result.
Actual protected reading is recorded separately. Native OS preference switching
was not exercised; reduced-motion behavior was verified in mounted tests.
The broad 38-domain/10-journey baseline and earlier six real model calls
remain historical evidence. They were not rerun as a new clinical or AI evaluation.

The full frontend suite was run on base source f962196. Native reading found a
chapter heading partly covered by the sticky header; final source 65c5bc5 adds
one scoped scroll-margin rule. The final build, independent narrow review and
protected desktop/mobile heading checks passed after that repair. The original
observation and correction are retained in the browser acceptance receipt.

## Exact operational checkpoint

The final read-only audit at **2026-11-15 03:31:45 UTC** confirmed the image and
source above, all 32 HTTP asset hashes (including 11 guide JPEGs), and HIS,
LabClear and DR readiness responses of 200. The latest foreground cron guard
was PID 1496026 / start ticks 32720080, with config hash
`44063bdd373d46caf96dd3400473baac2dc2f39ce3947c87d573e612fed1113b`.
Its current witness is
`/home/chaw/his-poc/var/user-guide-release-20261115/heading-followup/new-start-preexec.json`.
Older Admin/initial-guide witnesses describe previous processes and must not be
used as the current worker identity. This observation is dated, not a guarantee
that the same PID will remain current after a later authorized operation.

All database rows matched the 03:22 heading-followup baseline exactly. Compared
with the first guide baseline at 03:09, only ordinary test authentication changed:
two audit rows, one login attempt, one security event and one new session. One
existing test01 session changed only from an unset to a set revocation time.
Clinical/AI/account/membership rows, both specialist databases and source files
remained exact. The final audit queried persisted role grants before confirming
that the administrator had no clinical signer or wildcard permission.

The prior audit program was held and never executed after review found an
unsupported signer-permission assertion. The corrected version was independently
reviewed, hash-checked and executed once. Rollout and final-audit output remains
separate from clinical or model evaluation evidence.

## Operational boundaries

The guide reads no patient or encounter data, prepares no model request and
performs no account/clinical/financial mutation. The shell retains ordinary
session verification. The same backend and PostgreSQL 0005 remain authoritative;
all workflow and specialist services retain their own current permissions and
state transitions. No cloud, model, dataset, dependency or paid resource was added.
Access/Tunnel/DNS and the worker private environment remain unchanged.

The app-only rollout preserved current records and files, replaced image pins,
and rebound the existing foreground cron guard with a unique witnessed launcher.
Exactly the owned one-off was removed; original cron bytes were retained.
Recovery scripts retain current data and restore the immediately preceding 60d0d325 image;
rollback execution, exact fresh-dump restore and host reboot remain NOT_RUN.
The prior isolated 0005 restore is separate historical qualification.

Evidence: [local checks](../evidence/user-guide-20261115/local-qualification.json),
[runtime](../evidence/user-guide-20261115/runtime-readback.json),
[preservation](../evidence/user-guide-20261115/preservation-readback.json),
[browser](../evidence/user-guide-20261115/browser-acceptance.json).
