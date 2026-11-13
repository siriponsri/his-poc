# Executable backlog — full-system scope

F0–F5 are active scope; historic B00R–B06R is superseded. Actual completed/remaining detail is maintained in DOMAIN_COVERAGE.json and VALIDATION_REPORT. Never relabel a menu as an implemented domain.

| ID | Work | Acceptance / dependency |
|---|---|---|
| FS-01 | Reproduce new release on native PostgreSQL18 or Compose | fresh migrate, explicit deterministic seed, app ready, login; no reset |
| FS-02 | Close every matrix gap D01–D38 | domain form/list/detail/service/FK/transitions/audit + PG happy and negative evidence |
| FS-03 | Execute J01–J10 with real browser and PostgreSQL | role/patient transitions and cross-module record IDs; deep-link/reload/mobile/session clearing |
| FS-04 | Concurrency/fault/restore acceptance | no duplicate or partial dispense/stock/payment/result; isolated PG+files restore hashes |
| FS-05 | Scope/credential/revoke and source-staleness adversarial tests | direct API+tool guards; version/approval invariant; no stale client context |
| FS-06 | One named live inference route | exact artifact/runtime/template, endpoint, data policy and budget confirmed; separate evaluator |
| FS-07 | Clinical/product/payer pilot evidence | hospital/SOP/intended-use owner and authorized data; not inferred from mock tests |

First action for a receiving Codex: read current validation/coverage, run FS-01, then fix the highest unfulfilled FS-02/FS-03 acceptance using existing shared schema rather than a new app. Do not wait for model keys to do FS-01–05. Exact commands and observed blockers appear in START_HERE/CODEX_HANDOFF.

## Checkpoint status 2026-11-13

FS-01 native PostgreSQL PASS; Docker/Windows NOT_RUN. FS-02 all38 local implementations present; browser acceptance pending. FS-03 API traces10/10, browser NOT_RUN. FS-04 PostgreSQL concurrency/restore PASS, rendered fault UX pending. FS-05 core/backend and component regressions PASS; browser adversarial checks pending. FS-06/07 UNKNOWN resources and NOT_RUN; no activation authorization assumed.
