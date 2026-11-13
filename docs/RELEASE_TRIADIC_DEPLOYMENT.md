# Triadic redesign and named-host deployment contract

Owner request:13 November2026. Base39f788fa956e09bc4a87f200b63aef92cfcd8698.
Scope: full React UX/UI redesign, existing behavior preserved, plus deployment and actual URL acceptance at his.ai-cie.com on dr-train.

## Constraints

Use exact anchor colors #1C4286, #861C42 and #42861C with neutral working surfaces. Apply the user-named no-slop-ui and Hallmark guidance in app scope; preserve runtime data, permissions, shared identity, immutable evidence, human approval and durable retry semantics. No invented charts, clinical claims, copied competitor assets, paid API, model installation or changes to shared remote Ollama.

Root integrates and publishes. triadic_frontend owns frontend/design evidence. deploy_dr_train owns dedicated Linux deployment, private credential transfer and data-copy verification. triadic_review independently reviews usability. Local User-folder skills and role contracts are read; concurrent ownership is non-overlapping.

## Acceptance

1. A substantive task-oriented redesign of shell/home, records/forms, document and AI review surfaces, with responsive states and keyboard behavior.
2. Existing frontend regressions plus meaningful new flow tests pass; independent no-slop review and actual desktop/mobile checks reference the candidate.
3. Windows synthetic DB/files are preserved and copied into a separate dr-train HIS database/file location; compare all table counts and file checksums, prior live result retained.
4. Dedicated app loopback18080, DB loopback15432, existing model loopback11434; no unrelated service restart. Persistent app/DB/connector lifecycle and rollback.
5. Secure HIS cookies, exact HTTPS origin, server-side scope/CSRF and Access-required exact-host tunnel. No backend or model API public bypass.
6. Real HTTPS hostname serves the exact reviewed build; unauthenticated boundary denies API/content; allowed browser executes login, source-bound real AI review, human edit/approval/commit and reload.
7. Keep failed/skipped/unexecuted checks explicit. Integration is not clinical effectiveness.

The existing Access app was independently inspected read-only: exact hostname/all paths, one Allow policy with three email includes, user-provided audience matched and no Bypass policy observed. Public acceptance remains a separate gate.

## Deployment placement

Server discovery found no existing HIS checkout and an unrelated listener on8000. Dedicated root is /home/chaw/his-poc. Preserve Windows application data and shared server workloads. User-provided private tunnel credentials are transferred directly over authenticated SSH and never committed. Original Windows private Cloudflare settings remain a prior placeholder; the server uses a newly verified private profile.

Execution evidence is reconciled below and in the final named section of VALIDATION_REPORT.md.

## Completed acceptance

All seven named acceptance criteria passed in their stated synthetic scope. Frontend25 unit/69 component/audit/typecheck/build; independent six-section review and13 actual responsive observations; initial isolated data copy109 table counts/one file exact; final48 runtime source/21 built asset hashes; secure private listeners/cookies; exact-host Access gate5/5; actual public document→real Typhoon→human editv2→approve→commit→reload.

Canonical receipts: evidence/triadic-release/public-final/browser-acceptance.json and access-boundary.json; evidence/deployment-20261113/public-workflow-readback.json, final-deployment-verification.json and final-resource-verification.json. The actual public call took10414ms with422 input/136 output tokens and unmeasured cost. One attempt/result and version/hash-bound approval were verified. Existing Windows data, prior live result, test01 and sessions were retained; final app replacement did not restore/seed/reset the database or restart connector/Ollama.

Deployment documentation and metadata were reconciled after the immutable runtime snapshot. Git source publication is a separate step and does not trigger deployment. Real patient/clinical/product evaluation and unrelated connectors remain outside this release. Current operations/backup/rollback: docs/DEPLOY_DR_TRAIN.md.
