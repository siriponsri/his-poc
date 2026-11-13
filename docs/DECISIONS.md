# Current decisions and supersession

Historical ADR001–018 remain in `history/v0.2/docs/DECISIONS.md`; they describe the old demo. Current user scope overrides singleton, SQLite-primary, public bearer identity and placeholder-only domain delivery limits.

| ID | Decision | Reason / verification boundary |
|---|---|---|
| ADR019 | Expand existing React source and tested invariants in isolated v0.3 workspace | preserve immutable v0.2 ZIP and actual baseline; no unknown repository overwritten |
| ADR020 | FastAPI modular monolith, SQLAlchemy/Alembic, PostgreSQL18.6 | current user specification; actual dependencies pinned; PG runtime checked independently |
| ADR021 | `/api/v2` typed object contracts; default v1 unmounted | avoid silently changing stringified v1 DTO/auth; historical tests isolated |
| ADR022 | Server session and scoped local roles, clinical signer separate from admin | user requires real login and permissions; no client role selector grants |
| ADR023 | Reuse shared UI primitives and domain metadata, with domain-specific relational services | solo maintainability; metadata renderer is not acceptance of a domain on its own |
| ADR024 | Immutable new revisions, forensic read-only legacy archive | old SQLite can lack original source; never invent unavailable revision |
| ADR025 | Explicit synthetic mock and local integration acknowledgements | no authorized model endpoints/paid API/payer access; all unknown inventories retained |
| ADR026 | Native isolated PostgreSQL execution in review environment; Compose offered separately | Docker unavailable here; native PG evidence cannot be relabeled Docker/Windows evidence |
| ADR027 | Strict L2/L3 reporting; checkpoint when browser/invariants not evidenced | browser unavailable does not mean implementation missing, but prevents full L3 gate |
| ADR028 | shadcn base, approved other repos optional references | retain actual provenance, do not claim Magic UI/Motion installed without source/lock evidence |

Reversible defaults: synthetic organization/facilities, UTC timestamps, decimal money/quantity, allowlisted manual actions, local file store and explicit seed. No automatic clinical diagnosis/dose/triage/blood-compatibility. No deployment/paid API/training or real server modification occurs in this release.
