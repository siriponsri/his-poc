# API implementation boundary

Current: FastAPI `backend/app/main.py`, `/api/v2`, server-backed cookie sessions and CSRF. Core DTOs are typed Pydantic models; clinical and ERP catalogs map to separate domain DTOs and validators. Exported OpenAPI/domain JSON Schemas are in `contracts/v2`. Run `python scripts/export_contracts_v2.py` after intentional contract changes, then tests.

No default v1 mount. `/api/v1/context` and old demo tokens do not enter the new database or authentication path. Historical v1 behavior is retained in isolated src/his_poc tests only. This is an explicit API/authentication migration, not wire compatibility.

`backend/INTERFACES.md` documents shared dependency, actor/scope, transaction, idempotency and DTO conventions. Lists use `{items: [...]}`. Decimal amounts/quantities serialize as strings. Existing-record writes carry expected version and business mutation identity. Server responses are authoritative for revision binding; unknown write outcome requires identity-matching replay/read-back.

Access checks apply to reads/actions/exports, not only menus. Care assignments, patient portal ownership, active membership and current permissions affect scope. Document content and dataset export have separate permissions. Operational backup is a configured platform-operator capability since its snapshot contains all organizations; a facility role alone does not grant it.

Executed API/PG/HTTP evidence and limitations are in VALIDATION_REPORT and per-domain coverage. API availability or OpenAPI schema count does not prove domain/clinical effectiveness.
