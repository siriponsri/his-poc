# Administration API reference

[openapi-0005.json](openapi-0005.json) contains only the actual administration
routers and their transitive request/response schemas. Generate it with
`python scripts/export_admin_contract.py` from the repository root. Importing
the application constructs the API schema without connecting to PostgreSQL,
seeding an account or invoking a model.

This additive reference preserves the older full exports. Migration remains
`0005_assistant_workspaces`; no database change accompanies this console.
The [operator guide](../ADMIN_OPERATIONS.md) describes scope, concurrency,
password-policy separation and explicit private provisioning.
