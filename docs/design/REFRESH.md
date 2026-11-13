# CareBalance frontend refresh

Date: 13 November 2026. User-selected palette: yellow / gray / purple / orange. Existing green identity is superseded for this interface.

Operate mode: clinical and administrative staff complete tasks, inspect source documents and review results. White surfaces, warm gray canvas, purple primary action, yellow selection and orange attention. Readable self-hosted IBM Plex Sans Thai, compact named navigation, visible patient/encounter context, fine dividers and progressive detail.

The incoming Claude work was preserved under ignored var/frontend-before-refresh before editing. Useful typed records, i18n, status patterns and real workflows were retained. Changes reduce greeting/marketing copy, shorten navigation labels while retaining full accessible names, fold secondary home/history/results content, and make recorded evidence readable. No fake charts, account roles, statistics or AI outcomes were added.

Primary flow: sign in → choose workspace → choose patient/encounter when needed → inspect/create record → review bound proposal → approve → commit. Loading/error/pending/conflict and disabled states remain explicit. Historical live/mock results retain their own source labels. Exact source quotes are not clinical validation.

Baseline incoming source:25 unit/60 component checks PASS, audit/typecheck PASS. First post-edit run retained an obsolete greeting assertion failure. Updated semantic tests preserve identity/counter/logout checks. Final themed checks:25 unit/63 component PASS, audit/typecheck/build/runtime dependency audit PASS. New regressions cover ShowAll at6 domains, keyboard tab focus, and unique accessible IDs.

Browser evidence is under evidence/frontend-refresh. Preview inspection and final production-build confirmation remain separate; neither invokes a new model or makes clinical/data mutations. Persisted live Typhoon results are read back instead. See VALIDATION_REPORT.md for executed final details. References and reuse boundaries: REFERENCE_REVIEW.md.
