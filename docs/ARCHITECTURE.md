# Full-system architecture

Current application: React/TypeScript/Vite → same-origin FastAPI `/api/v2` → SQLAlchemy PostgreSQL18. Domain routers share one identity/session, one patient/encounter core, one unit of work and one audit/operation boundary. SQLite/std-library server remains isolated historical regression; it is not mounted by the application. `/api/v1` default returns404. No new response shape is inserted under v1 routes.

```mermaid
flowchart TD
  UI["React • login / workspaces"] --> API["FastAPI • session / CSRF / scope"]
  API --> CORE["Shared core • evidence / tasks"]
  API --> DOMAIN["Clinical / ERP services"]
  CORE --> DB["PostgreSQL • relational records"]
  DOMAIN --> DB
  DOMAIN --> FILES["Local file adapter • checksums"]
  CORE --> AI["AI provider boundary"]
  AI --> MOCK["Explicit synthetic mock"]
  AI --> LIVE["Opt-in dr-train • synthetic document review"]
  LIVE --> TUNNEL["Loopback SSH forward • existing Ollama"]
```

## Ownership and transactions

`backend/app/models.py` owns organization/facility/user/session/patient/encounter/task/document/order/AI/audit/operation records. `models_clinical.py` and `models_erp.py` own their relational tables. Domain relationships point to shared IDs. JSONB is used for snapshots, model outputs, event details and analytics snapshots; identity, quantities, money and core relationships remain relational.

Core schema/interfaces are in `backend/INTERFACES.md`; generated reference DDL and OpenAPI are in `contracts/v2/`. Apply Alembic migrations, never generated reference SQL. Important subject relationships use DB foreign keys, domain services recheck ownership and expected versions. Readiness must verify schema version and DB connection; startup does not create or seed tables.

A successful mutation must complete its transaction before the success response. It revalidates current account/membership/session, scope, permission, entity state/version, and domain invariants. Operation identity is actor+idempotency key bound to canonical payload and operation. The same operation replays its stored response; different content conflicts. Domain writes and audit/operation records commit together. Stock, bed, slot and financial records use row/advisory locks and constraints where implemented; executed concurrency cases are listed in validation rather than inferred from locking code.

## Authentication and frontend state

Local development accounts are stored server-side with Argon2 password hashes. Opaque session token is stored in HttpOnly SameSite cookie; server stores token hash and expiry/revocation. CSRF token guards authenticated mutations. HTTPS configuration adds Secure; local loopback HTTP is explicit. Production OIDC/MFA remains outside local acceptance.

Frontend loads identity/permissions from `/auth/me`, clears record/context/draft state on session changes, and scopes clinical queries to selected patient/encounter. Response identities and versions bind display/action state. Mutation success updates its returned record before optional refresh. Definitive no-write conflicts clear pending; transport ambiguity retains operation key until matching read-back or replay confirms. A successful unrelated GET never confirms a commit. Skip-link focus does not modify route; deep links resolve through same-origin SPA serving.

## Documents and AI

New document revisions are immutable with canonical hash/version references. Attestation is an authenticated internal action, not an asserted legally qualified signature. Amendments preserve previous revisions. Proposals bind task, evidence revision and encounter version; edits increment proposal version and invalidate approval; commit rechecks evidence and current authorization. Failure/timeout/abstention create run records without synthetic success hidden behind them.

The default provider is a deterministic demo adapter with synthetic inputs. No live fallback exists. `config/` retains observed model/runtime metadata and defaults; application deployment is independent of inference placement. Unknown usage/cost stays null. DR/CAD interfaces/evaluators remain separate. Local manual image/report workflows are not live predictions.

## Files, integration and operations

File records bind checksum/MIME/authorized clinical owner; local bytes live in a configured directory. Backup must include PostgreSQL and file manifest, and restore verifies both in an isolated target. Integration module records synthetic inbox/outbox delivery/retry/acknowledgement as local, never external successful transmission without an endpoint.

Financial summaries retain gross receipts and refunds separately; net=gross-refunded. Outstanding uses invoice adjustments, payment allocations and explicit allocation releases. Posted amounts and stock movements are not overwritten by returns/reversals. Allocation/cost definitions and measured tests appear in WORKFLOWS and validation.

Canonical target is `spec/`; actual implementation and remaining gaps are `DOMAIN_COVERAGE.json`. This architecture does not itself certify every invariant or every domain as tested.

## Denial-audit concurrency and support visibility

SecurityEvent recording is synchronous database work dispatched through run_in_threadpool from the async HTTP middleware. Its actor foreign key can wait on another request's identity lock; the event loop must remain free to complete that request and commit. Domain write/audit/idempotency transactions remain unchanged. A live Uvicorn/PostgreSQL regression holds the real FK lock and verifies health responsiveness before releasing it, then checks the persisted denial event.

Entity-scoped audit reads for ERP support records require their domain permission, organization/facility scope and membership in the existing actor-visible rows policy. In particular, a nurse can inspect their own staff audit while quality users retain authorized staff oversight. Imaging file bytes require document content/export rights in addition to D11 record scope, and successful downloads create a bounded checksum audit event.

## Opt-in live document completeness

HIS_AI_PROVIDER=dr_train_ollama plus HIS_LIVE_SYNTHETIC_ENABLED=true selects the native Ollama adapter for document_review only. Startup/requests fail closed on missing settings, unknown providers, engine-version/model-manifest mismatch or unsupported tasks; no mock/cloud fallback. Registries describe observations; environment settings are the runtime authority. Source is untrusted data; output must match a fixed five-key JSON schema and each nonempty quote must occur verbatim in the referenced document. These controls do not validate clinical or semantic correctness.

The API commits an actor/key-bound InferenceRun reservation and started audit, then closes its database session before awaiting external inference. PostgreSQL advisory admission permits one active unexpired run across users/workers. Same-key pending requests receive202 without another call; conflicting payloads409. A lease derived from configured timeout plus60 seconds retains interrupted outcomes after expiry. The provider uses an absolute asyncio deadline around the whole HTTP pipeline, bounded context/output and pinned metadata. Transport cancellation does not establish remote-engine cancellation.

A fresh transaction rechecks session/account/permissions, patient/encounter/task domain and versions, document revision and evidence hashes before persisting a proposal. Stale, revoked, busy, malformed, abstained, failed and timeout outcomes remain recorded. Success writes proposal/version/audit/idempotency together. The frontend renders five typed findings and actual run provenance; only the human review/approval/commit flow writes a final result. Edits preserve the report and create a new action hash/version. Migration0002 adds nullable reservation/provenance columns and the actor+operation-key uniqueness constraint; historical rows remain intact.

## Observed protected server placement

The separately authorized synthetic POC is deployed on dr-train under /home/chaw/his-poc. Cloudflare Access and an exact-host JWT-required Tunnel route his.ai-cie.com to127.0.0.1:18080. The dedicated app uses an isolated PostgreSQL18.6 instance at127.0.0.1:15432 and persistent file/backup volumes. Existing Ollama stays on127.0.0.1:11434. No model/database public route exists. App/DB/connector restart unless stopped with bounded resources; metrics remain loopback. This is deployment integration evidence, not a production HA claim.

Windows synthetic data was read-only exported and restored once to the new isolated server volumes with109table-count/onefilehash verification. Subsequent server writes are independent; no automatic synchronization or restore-on-start. A source snapshot builds an immutable image; a Git push alone does not deploy. See DEPLOY_DR_TRAIN.md for current runtime, backup and rollback, and evidence/deployment-20261113 for the observed bindings.
