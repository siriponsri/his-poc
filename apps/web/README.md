# CareBalance HIS POC frontend 0.3.0

React + TypeScript + Vite application for the PostgreSQL full-system development prototype. The root opens real local authentication. All business calls use same-origin `/api/v2`; session cookies remain HttpOnly, CSRF is held in memory, and provider credentials never enter this bundle. No public demo bearer UI or fixture-to-live fallback is mounted.

From this directory, Node 24:

```bash
npm ci
npm run sync-full-catalog
npm test
npm run test:component
npm run test:audit
npm run typecheck
npm run build
npm run dev
```

Start the FastAPI/PostgreSQL application following root START_HERE.md. Vite development uses loopback port5173 and `/api/v2` proxy to `HIS_PORT` (default8000). For the single-origin production build, build here then run the root FastAPI app; it serves `dist` and deep-link fallback. `vite preview` alone has no API backend. Docker/native launchers belong to the root operations package. No SQLite fallback exists in the mounted frontend.

The shadcn sidebar-01 shell remains the component basis with its pinned MIT source and notice. Navigation, form primitives, typography and the full-system screens are locally authored extensions. Magic UI, shadcn-admin and Impeccable were inspected as authorized references, with no new code from those repositories copied into this frontend. See TEMPLATE_PROVENANCE.json and root evidence/fullsystem/references. Fonts use installed IBM Plex Sans Thai if available, then Tahoma/system fallbacks; no external font request is required.

## Implemented screens

- Login/session bootstrap, server-confirmed membership context, role home counters/worklist, logout and401 expiry cleanup; distinct patient-portal navigation.
- D01 patient create/verify/activate/deactivate and demographics PATCH; D03 encounters; D07 typed orders/revisions/transitions and tasks; D22 immutable document revisions/content hashes; D34 user/membership/care assignment/session administration; D37 explicit mock proposal/review/commit; D38 actual allowlisted operations jobs.
- Eighteen clinical and thirteen ERP modules use backend-authored typed field/action catalogs copied by `sync_full_catalog.py`. Each resource has semantic fields, legal state actions, list/search/detail and history. This shared rendering is not a JSON editor and creates no fake transactions. Supporting resources include prices, coverage, charges, supplier/item/lot/warehouse registers, budgets, staff credentials, reservations/counts and dataset access.
- D11 uses a synthetic PNG/TXT chooser with internal encoding, D15 shows raw measurements over time, D20 has authenticated referral download, and D21 reads only server-published own records. Pending outcomes retain the same idempotency payload/key for retry. Decimal inputs preserve strings; datetime-local inputs become timezone-aware ISO.

## Audit fixes and testing boundaries

F20-01 through F20-03 were reproduced against untouched v0.2 source, then patched before the new UI. `legacy/App.v020.tsx.txt` and `legacy/App.audit-fixed.tsx.txt` preserve both; the old app is never mounted. `test:audit` uses the original pre-render reproducer against the fixed historical source. F20-04 uses focus navigation separate from pathname routing and explicit404.

`test:component` mounts the actual React app in jsdom: login/logout, scoped home, denied routing, focus/404, all38 typed module controls, revision+failed refresh recovery, definitive409, exact-identity lost-response reconciliation, decimal/time conversion and delayed-selection race. Its transport is controlled test doubles: it is component evidence, not PostgreSQL or browser proof. Root integration suites separately verify PostgreSQL transactions.

Browser execution is NOT_RUN in this environment because Chromium launch is blocked by socket permissions. No visual, layout or browser accessibility assertion is claimed. The optional smoke runner uses an already running isolated synthetic app:

```bash
# HIS_SEED_PASSWORD must already be set securely to the local seed password.
HIS_BASE_URL=http://127.0.0.1:8000 python scripts/browser_check.py
```

It tests login, create/reload, denied route,404, logout, portal and mobile navigation, and records executed assertion counts. This is smoke coverage; full J01–J10 browser acceptance remains a separate outstanding milestone in the root handoff. Do not relabel component/API tests as browser PASS.

Historical v0.2 fixture data/adapters/tests and optional script snapshots remain isolated for migration/audit regression only. `sync-data` updates those historical fixture inputs; it is not the v2 runtime seed. New patient data comes exclusively from PostgreSQL APIs and the explicit root seed command.

## Authored canonical browser scenarios

`python scripts/browser_journeys.py` drives J01–J10 through rendered UI against an **isolated clean seeded app** on loopback8000. It changes synthetic records and creates an actual local backup in J09. All actors use the explicit local seed password from `HIS_SEED_PASSWORD`; no password is embedded in the script. Do not run against an owner working dataset. The script does not reset/drop a database.

The authored scenarios cover appointment/queue→encounter→care grant→document→AI edit/review/commit (J01); lab/correction/acknowledgment (J02); dispense/return with lost-response retry (J03); emergency/admission/transfer/handover/discharge/followup (J04); invoice/claim/remittance/receipt/refund/cost (J05); procurement/partial receipt/stock return (J06); identity/scope/revocation (J07); image-file/report/mock review/referral (J08); maintenance/CSSD/linen/facility/CAPA/report/backup job (J09); and published own result/portal request/staff booking (J10).

These scripts were syntax-checked but browser execution is **NOT_RUN** here. On the recipient's machine they write per-journey PASS/FAIL/NOT_RUN and exact observed record IDs; the first failure leaves subsequent journeys NOT_RUN. A scenario PASS is evidence for its described actions, not automatic full-system certification. Negative API/concurrency/restore requirements and the canonical acceptance checklist remain separate. `browser_check.py` is the shorter startup smoke; `browser_driver.py` supports the canonical scripts and never writes directly through an API client.
