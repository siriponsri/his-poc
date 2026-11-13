# Independent migration and implementation review

Reviewer scope: baseline v0.2 reproduction, approved UI repository provenance, forensic legacy importer, and targeted source review of the concurrently implemented PostgreSQL application. This is not a claim of complete clinical, security or full-system acceptance.

## Executed evidence

- Unmodified v0.2 baseline in `revision/HIS_POC_Starter`: Python 45 tests, legacy UI 12 tests, React adapter 17 tests, contracts/data checks, frontend typecheck and build all exit 0. Fresh logs and command records are in `baseline/`.
- Legacy importer: 6 stdlib source inspection tests plus 4 PostgreSQL 18.6 tests PASS (10 total). PostgreSQL tests run in a disposable real PostgreSQL cluster, cover retained rows after reconnect, idempotent import, changed mappings, missing original evidence, scoped reads, denied new legacy commit, revoked permission, and CLI password verification/session revocation. See `baseline/legacy-import-pg.txt`.
- Importer tests create the relational schema with SQLAlchemy metadata in their isolated test database; these results do not replace the separate Alembic migration/upgrade tests.
- UI repository metadata, README and license files reviewed through GitHub. Exact refs and Git blob identities are in `references/review.json`. Review did not copy any new component code.

## Findings communicated to owners

| Finding | Location / consequence | Resolution observed during review |
|---|---|---|
| Single-column and composite FK names collided | Core metadata naming; PostgreSQL failed schema creation | Changed to all-column FK names; importer schema test subsequently PASS |
| Transaction dependency could commit after response | FastAPI yield scope | Core/domain dependencies changed to function scope; global acceptance tests must verify commit failure response |
| Revocation refresh reused cached User/Session | `auth.revalidate_actor` | Locked User + populate_existing and refreshed Session observed |
| Idempotency response could cross active facility | `common.begin_operation`, core operation read | Org/facility payload hash and persisted scope added; actor/context replay requires independent API evidence |
| Operations dynamic route shadowed jobs/health | Router registration order | Operations router now registered before core dynamic operation route |
| Clinical writes checked stale permissions first | Clinical mutation entry | Owners notified to refresh actor before permission check |
| Medication could consume wrong item lot | D08 dispense | Explicit item reference and lot matching added by clinical owner |
| Medication return omitted stock movement | D08 return | Owner notified to append quarantined movement in same transaction; final journey tests must verify conservation |
| File store env mismatch could omit images from backup | Clinical HIS_FILE_ROOT vs operations FILE_STORAGE_ROOT | Owners coordinated canonical FILE_STORAGE_ROOT and DB-reference checks |
| Credential suspension applied only to ERP | `actor_for` / domain checks | Central permission derivation now filters credential privileges |
| D35 duplicate identity could expose another facility's record | ERP integration message create | Owner notified to scope dedup and validate linked referral type |
| D36 raw snapshot GET bypassed export/revocation boundary | ERP dataset detail/export | Owner notified to separate metadata preview from permission-gated export and reject revoked export |
| Generic AI completion could finish arbitrary order task | AI proposal target | Core owner notified to restrict allowlisted AI use-case task kinds |
| Forbidden requests lacked retained audit/security outcome | Authentication and request failures | Core owner notified to persist bounded metadata after rollback without tokens/bodies |

The integrator must use final code and rerun evidence for closure. Source observations here do not substitute for PostgreSQL/browser journeys or certify every finding as closed. `DOMAIN_COVERAGE` and `VALIDATION_REPORT` own final release status.

## Full-system matrix review snapshot

`matrix-review.json` records each of the exact 38 supplied acceptance cases, observed substantive implementation, concrete remaining evidence limits, test definitions and source hashes. It intentionally assigns no blanket L2 level. The ERP execution artifact confirms 13 tests and the operations artifacts confirm 11 PostgreSQL tests plus 6 launcher tests. Browser interaction remains NOT_RUN; the successful same-origin HTTP smoke is separate evidence.

Additional review-driven corrections observed: global operational backups now require a server-only platform-operator allowlist in addition to scoped D38 permissions; ordinary readers receive redacted job metadata. UI demographic updates, signed-order revision, historical document content, decimal-string inputs and stale response generation guards were added. Clinical owners added correction requests, scheduled rehabilitation sessions and immunization records; their fresh execution must be tracked separately. Per-domain evidence gaps remain explicit in the matrix review.

Final importer rerun: 10 tests PASS on actual PostgreSQL after requiring `documents.content` for archived narrative results; `D22.read` alone is insufficient. The negative content-permission assertion is included in the existing scope test. No migration/model change was required.
