# PostgreSQL application backend

FastAPI modular monolith, API v2. Run from archive root. The old stdlib SQLite API is not mounted into this application. Its public bearer tokens cannot authenticate v2.

```
python -m pip install -r requirements-backend.txt
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Set `DATABASE_URL` to an explicit PostgreSQL connection and `HIS_SEED_PASSWORD` to a development-only password of at least 12 characters before seed. Seed is explicit and versioned (`seed_runs`); a completed seed will never reinstate deleted permissions or replace application edits. New seed versions require reviewed additive data migrations. Server startup never seeds or migrates. For Compose/PowerShell use root operations instructions.

Core schemas and service contracts: INTERFACES.md, FastAPI OpenAPI `/api/v2/openapi.json`. PostgreSQL schema is frozen in migrations/schema_0001.py, initial revision0001_fullsystem. Future release schema changes need new Alembic revisions. `scripts/freeze_initial_schema.py` is a prerelease build tool, not an upgrade command. Downgrade is deliberately unavailable; restore into an isolated database and verify instead.

## Identity and transaction policy

Local accounts use Argon2id library defaults customized to 64MiB/time3/parallelism4; sessions are random256-bit-equivalent tokens, only SHA256 token digests persist. The CSRF token persists server-side and is returned by `/auth/me`; it is not an authentication token. HttpOnly/SameSiteStrict cookie, Secure toggled only for explicit HTTP loopback development. Every mutation must carry X-CSRF-Token; business writes also carry Idempotency-Key. Role-permission assignments are relational; current membership, care assignment and credential status are re-read at service mutation entry. Portal sessions have one patient subject and cannot accumulate staff privileges.

Clinician/nurse data scope uses explicit care_assignments; registration users can create patients but an administrator grants a clinician's care assignment before the clinical workflow. System administration does not imply clinical approval. `documents.content` and `documents.export` are separate from metadata read, so billing/registration document lists do not reveal full clinical narrative.

All database dependencies use FastAPI function scope: commit/rollback completes before the success response can be sent. Integration tests inject a before-commit fault and confirm409 plus no persisted partial patient. PostgreSQL foreign keys enforce encounter/patient/org/facility consistency; immutable revision/result/audit tables have update/delete triggers.

For this development prototype all mutation services acquire an organization advisory authorization fence before user/entity locks. This serializes role/credential/scope revocation with business transactions and prevents reviewer/admin lock-order inversion. This is a conscious throughput tradeoff; it is not a high-concurrency production architecture claim. Entity row locks, positive balance constraints and idempotency uniqueness still enforce domain invariants. A future performance change must preserve revocation race and concurrency tests.

Operation replay is bound to actor, organization/facility, permission/care-scope fingerprint, operation name and exact canonical payload. Changed authorization can deny replay even when a write previously succeeded; read current authorized entity/result and reconcile by proposal/version/hash/key. A different key cannot create a second AI result for a task/proposal. Unknown transport outcome is distinct from a definitive rejected transaction.

## Evidence, AI and audit

Document content is immutable by revision. Current revision is a deferred composite foreign key to a revision owned by that document. Attestations bind the immutable version and hash; amendment creates a new revision, never an overwritten signed record. Content revision numbers and lifecycle status have distinct meanings: status-only document actions do not invent new content revisions.

AI tasks are allowlisted review tasks in D37 (`document_review`, `imaging_review`, `dr_review`). They cannot complete a generic medication/lab/order task. Proposal versions bind exact canonical action bytes, immutable source revision, encounter version, task version and expiry. Review edits return pending; commit checks current reviewer permission/credential/care scope and target state. Failure/timeout/invalid/abstention attempts are retained with measured elapsed time; unknown cost/usage is null.

`providers.py` holds the provider boundary. Only explicit `HIS_AI_PROVIDER=mock_demo` is operational. Any other value returns `LIVE_PROVIDER_NOT_CONFIGURED` with no fallback; endpoint/checkpoint capabilities remain separately unverified. The immediate local deterministic mock performs no external inference. A future live adapter must use capture→close transaction→infer→revalidate/write units of work, not call network inference within the current mock transaction.

Read-only audit exposes metadata and version/hash identities, not raw passwords/session cookies/model reasoning. Denied API events persist separately after rejected request transactions; if security-event persistence itself fails a response header says so instead of fabricating audit success. Backup operations are restricted to development operators and include global-database backup capability: that permission is not delegated to clinical roles.

## Reproduce core verification

```
python scripts/test_with_postgres.py --pg-bin /path/to/postgres18/bin -- python backend/tests/run_core_validation.py
```

This creates a disposable PostgreSQL18 cluster, then migration, explicit seed, Alembic drift check and HTTP TestClient/database tests. It is not a browser test. `evidence/fullsystem/core-validation.txt` is actual execution, `core-journeys.json` contains J01/J07 actor and persisted IDs. Tests for clinical/ERP/operations/legacy import live in their documented suite locations. Live models, clinical effectiveness and external system certification are separate NOT_RUN scopes.
