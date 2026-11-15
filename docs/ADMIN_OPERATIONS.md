# CareBalance administration

This extension uses the existing PostgreSQL0005 identity/session/permission
contract. It adds no schema migration, automatic account creation, provider
probe, model generation or host operation. A source change or test result is
not evidence of deployment or provisioning on dr-train.

## Read-only overview

`GET /api/v2/admin/overview` requires both persisted `D34.read` and
`identity.admin` permissions in the session's current organization/facility.
Auditor, clinical, nursing, registration, laboratory and portal roles do not
gain this endpoint through their normal memberships.

| Field | Meaning and scope |
| --- | --- |
| `scope.organization_id`, `scope.facility_id` | Authenticated server scope |
| `users.total/active/suspended/disabled` | Organization-wide user counts |
| `sessions.active/revoked/expired` | Organization-wide session record counts; revoked takes precedence over expired, so the three counts are mutually exclusive |
| `security.recent_denial_count`, `window_hours:24` | Current-facility `request_denied_or_rejected` events with401/403/404/409/422/429, in the inclusive preceding24hours; successful operator events are excluded |
| `database.reachable`, `migration` | Successful database access and actual Alembic revision observed in this request |
| `assistant.configured/route/engine_version/profiles_qualified` | Allowlisted fields from local provider configuration; no endpoint, token or host address |
| `assistant.counts.queued` | Current-facility persisted `queued` plus `waiting_for_capacity` runs |
| `assistant.counts.running/succeeded` | Current-facility persisted execution states, not live engine telemetry |
| `assistant.counts.failed` | `failed`, `timeout`, `invalid_output`, `abstained`, `interrupted`; retained `stale_context` is not included in this grouping |
| `assistant.counts.awaiting_review` | Persisted successful runs whose review state is `pending`; current chart freshness and actor eligibility are not recomputed by this aggregate |
| `assistant.counts.active_watches` | Current-facility watches marked `active` with a future expiry |
| `assistant.live_status` | Always `not_checked`; configuration is not a health or inference test |
| `observed_at` | Server UTC observation timestamp |

The overview never selects assistant source manifests, generated notes or
clinical result payloads. It performs no HTTP/model calls. Pending review is a
subset of successful execution, not an additional mutually exclusive outcome.
Authentication and database failures retain normal API errors; an unavailable
database is not silently represented as an empty healthy dashboard.

## User list and memberships

`GET /api/v2/admin/users` retains its existing user projection and adds
`memberships:[{id,role,facility_id,active}]` per returned user. The projection
does not return password hashes, session secrets or CSRF values. Memberships are
persisted assignments, not inferred from a user's name. Organization-owned
facilities only are projected, including inactive and other-facility assignments
within that organization. Inconsistent legacy cross-organization memberships
are omitted.

Query parameters:

- `q`: optional case-insensitive literal substring of username/display name,
  maximum120characters. `%`, `_` and backslash are escaped as literal input.
- `status`: optional `active`, `suspended` or `disabled`.
- `limit`: default100, from1to200.
- `offset`: default0, minimum0.

Response: `{items,total,limit,offset}`. `total` uses the same organization/search/
status filters. Ordering is stable by username then ID. A single membership
projection query serves the selected page; the endpoint does not issue one
membership query per user. The count and page are ordinary request observations,
not a cross-request database snapshot under concurrent administration.

`GET /api/v2/admin/users/{id}` requires both `D34.read` and `identity.admin` and
returns the same safe user/membership projection by exact organization-scoped
ID, independently of list filters/pages. Missing or cross-organization IDs
return404. Use this endpoint to reload the exact user's version after an
optimistic concurrency conflict; a substring search is not an identity lookup.

`GET /api/v2/admin/sessions` retains its existing `identity.admin` guard and
session fields, adding `user:{id,username,display_name}` to every item. One
organization-scoped directory projection supplies these identities independently
of the user list's filter/page. Password hashes, token hashes and CSRF values
remain excluded. Use the nested server identity when confirming session revoke.

Existing version/CSRF/idempotency requirements for administration mutations are
unchanged. Removing the current actor's last active, persisted
`identity.admin`-capable membership in the current facility returns409
`SELF_LAST_ADMIN_MEMBERSHIP_REQUIRED`. The check executes under the existing
organization authorization advisory lock before changing membership/version.
Removing a redundant capable membership or a non-admin membership is permitted
by the existing API. This is not a new policy preventing all role assignments,
or a policy preventing an administrator from managing another administrator.

## Private named-POC administrator provisioning

The explicitly invoked module is:

```text
python -m backend.app.provision_poc_admin --username admin --organization org-demo --facility facility-demo --password-stdin
```

Supply the password privately through stdin from a protected prompt/process.
Do not put it in command arguments, shell history, source, examples, logs or an
environment variable. The program does not echo it. A minimal private prompt
wrapper can call `getpass.getpass()` and pass the result to `subprocess.run`
through `input=...`, without printing the value. Set the intended PostgreSQL
`DATABASE_URL` explicitly in the operator process before invoking the module.
Starting the application never invokes this command.

This is a narrow policy exception for the named synthetic POC:

- Only username `admin`, organization `org-demo` and facility `facility-demo`
  are accepted; organization/facility existence and ownership are verified.
- Current migration must be exactly `0005_assistant_workspaces`. No migration,
  seed, reset, permission backfill or role repair is attempted.
- Only this private CLI accepts8–200characters, without leading/trailing
  whitespace or embedded newline/NUL. Public create/reset password policies and
  the seed policy remain12characters minimum.
- The new user is active, uses the current password hasher, and has exactly one
  active `system_admin` membership. Persisted role permissions must exactly match
  the restricted system-admin template; permission drift causes a stop.
- The identity is not added to `HIS_PLATFORM_OPERATORS`. The initial membership
  has no clinical approval, attestation, order-signing, chart-content or assistant
  preparation capability. It is an identity administrator, not a clinical signer.
- Existing role-management authorization is unchanged. A separate explicit
  assignment is not silently performed by provisioning.

Creation, membership and its operator-origin security event commit atomically.
The existing organization authorization lock serializes concurrent provisioning
and membership administration. A repeated exact identity/scope/membership and
matching password returns `UNCHANGED`, without rehashing/resetting the password,
changing its version, adding memberships or duplicating the creation event.
Different password, inactive/mismatched identity, extra/inactive membership,
platform-operator identity, role-permission drift or wrong migration stops with
a fixed error code. Conflicts require investigation; this command never repairs
them by guessing or overwriting existing state.

Schema0005 `AuditEvent.actor_id` is non-nullable. The CLI therefore uses the
existing durable `SecurityEvent` ledger with `actor_id:null`, `method:CLI`,
event `poc_admin_provisioned`, status201, explicit organization/facility and
`/operator/provision-poc-admin/users/<created-user-id>` as its target reference.
It does not pretend that the newly created administrator performed its own
creation. An unchanged preexisting identity is not claimed to have been created
by this invocation. Normal administrator login and later actions retain their
usual authenticated audit records.

The CLI prints only fixed status/policy and identity/scope metadata. Database
errors are reduced to a fixed code; passwords, hashes, connection strings and
driver diagnostics are not printed. Exit0 means `CREATED` or `UNCHANGED`; exit2
means not provisioned. A lost response has an unknown outcome until the existing
identity and retained event are inspected; do not reset a password or rename an
identity to bypass a conflict.

## Local qualification

Run the admin-specific suite only through the disposable PostgreSQL18 wrapper:

```text
python scripts/test_with_postgres.py --pg-bin <PG18_BIN> -- python scripts/run_pg_suite.py backend/tests/test_admin_console_pg.py -q
```

The suite verifies actual PostgreSQL authorization/scope/counts, paging,
persisted membership projection, self-deactivation, concurrent/idempotent private
provisioning, conflicts, password-policy separation and initial clinical/operator
denials. It uses a generated test-only password, not the owner's credential.
These tests do not provision the real server, establish live AI health or replace
an authorized deployment/public-browser acceptance check.

Executed local qualification on15November2026 (Asia/Bangkok):35admin-specific
PostgreSQL18.6 tests plus3existing authentication/J07/session-revalidation
regressions passed (38PASS,15unselected core cases,18.25seconds). Ruff
F821/F401/F841 and Python compilation passed. The runner created a fresh
loopback-only disposable cluster and removed it afterwards. No live provider,
real-server provisioning, production database or deployment was used. The
existing Starlette/httpx test-client deprecation warning was retained.
