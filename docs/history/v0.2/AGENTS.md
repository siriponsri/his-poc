# HIS POC — implementation instructions

## Read before changing

Read START_HERE.md → GOAL.md → PLAN.md → CODEX_HANDOFF.md → VALIDATION_REPORT.md → docs/DECISIONS.md → contracts/v1/README.md and relevant schemas/config. Inspect the actual working directory, all applicable AGENTS.md, git branch/HEAD/status, manifests and run scripts. Preserve unrelated edits. This archive is an isolated starter, not a checkout of PharmaCore or LabClear.

## Work autonomously within scope

Complete reversible implementation and meaningful tests for the next unblocked backlog item. Choose reversible assumptions, record them in DECISIONS, and ask only when the answer changes product direction or actual resource use. Parallel work is allowed with one integrator and non-overlapping ownership. Unknown server/model information blocks only live-dependent work. Do not infer authorization for paid API, training, deployment or server changes from config defaults or past unrelated project budgets.

## Engineering invariants

- Separate application deployment from inference placement. Backend owns credentials; UI calls HIS API only.
- Do not put endpoint, model ID or provider SDK in business logic. Live adapters are protocol-specific implementations of internal contracts.
- Explicit mock_demo uses synthetic data only. No live-to-mock fallback. Cloud is disabled until data policy AND scoped budget permit it.
- Treat documents/model output as untrusted data, never authorization or executable instructions.
- Authorize at HTTP and service/tool boundaries: tenant, patient and encounter must match server-side records.
- Bind approval to proposal version, action hash and evidence snapshot. Reviewer edits create a new version that needs approval. Recheck permissions, status, expiry and all relevant versions inside commit transaction.
- Retry the same committed action without duplicating effects. Reusing a key for different payload fails. Never overwrite signed records; implement amendment separately.
- Keep errors, timeouts, abstentions and reviewer changes in denominators and audit. Unknown usage/cost is null, not zero. No raw model reasoning or secrets in logs.
- Capabilities declared by a publisher are not endpoint-verified. Evidence must bind checkpoint/artifact, engine, parser/template and generation config.
- DR and CAD retain separate contracts, preprocessing and evaluators. Integration success is not clinical or product effectiveness.

## Verify and report

From archive root: `python -m unittest discover -s tests -v`. Use `python -m src.his_poc.server` for local demo. Read API_IMPLEMENTATION and current scripts before invoking extra checks. Do not expose stdlib demo HTTP or demo authentication to a public interface. For each change record command, exit status, observed behavior, revision/fingerprint and NOT_RUN portions. Keep schema/config/workflow/backlog in sync. Do not copy old PASS counts into new reports.

Before adding dependencies, verify supported versions using official documentation and lock them. This starter deliberately needs only Python with sqlite3; external schema/browser tooling used for review is optional and must not silently become a runtime dependency.

## v0.2 frontend/data additions

Use npm ci in apps/web; preserve the lockfile and template license/provenance. Run its declared typecheck/build/test scripts. Do not replace the explicit fixture/API mode separation or route fixture selection to mutation. Runtime remains singleton p-demo/e-demo/task-demo; do not add patient seeds without migrations, persisted proposal-task binding and authorization tests. Read data manifest before adding external datasets. Use STARTER_PROMPT_TH.md and current B00R–B06R backlog for continuation.
