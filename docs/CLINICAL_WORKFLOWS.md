# Clinical workflow implementation and verification

The 18 clinical modules use the shared FastAPI session, PostgreSQL transaction, current permissions, facility scope, care assignment, patient/encounter foreign keys, audit and idempotency services. They contain domain-specific relational tables and typed inputs. They do not infer diagnoses, triage levels, medication doses, blood compatibility or treatment effectiveness.

`backend/app/domains/clinical.py` owns the runtime catalog and Pydantic input models. `clinical_catalog.json` is the frontend handoff snapshot. `domain_schemas()` exports the actual input schemas, including allowed action names. `backend/app/models_clinical.py` owns clinical tables; `backend/app/storage.py` defines the file-store interface and local implementation. The Alembic migration includes database constraints and immutable history triggers.

The common URL structure does not imply a generic JSON workflow: each module has distinct typed fields, legal state transitions, linked entities and service guards. There is no endpoint that accepts a raw table name, SQL or arbitrary model fields.

| Domain | Primary table | Minimum local workflow and checks |
|---|---|---|
| D02 | clinical_appointments | Requested → booked → checked_in → called → completed; slot lock enforces capacity; check-in creates one shared encounter and queue ticket; cancel/reschedule validated. |
| D04 | clinical_emergency | Manual arrival/assessment/care/disposition; admission request creates a D05 record once; referral disposition creates a shared D20 task. |
| D05 | clinical_admissions | Bed allocation/transfer/discharge; partial unique active bed/assignment constraints and row locks; old assignments retained; discharge releases beds and requires active devices to be released. |
| D06 | clinical_handovers | Nursing sign/receive/amend; designated receiver required; handover task links retain real shared task IDs/versions; no implicit medication administration. |
| D08 | clinical_medications | Signed order, item/code/name/unit/quantity binding; pharmacist review/dispense; eligible lot, stock movement and charge in one transaction; returns link original movement, enforce cumulative limit and increase quarantined stock only. |
| D09 | clinical_administrations | Reviewed prescription and manual matching dose/route; verify/administer/hold/not-given/correct; immutable original event snapshot and duplicate prevention. |
| D10 | clinical_labs | Signed order → collect/accession → receive → manual result → laboratory verify/release → clinician acknowledgment; corrections preserve prior snapshots and revoke prior portal publication/acknowledgment. |
| D11 | clinical_imaging | Signed order → schedule → allowlisted synthetic file → human report → imaging review/release/amend; file checksum/size/signature and scoped download; no PACS or live DR claim. |
| D12 | clinical_procedures | Room/time booking, human checklist, procedure/anesthesia documentation and closure; advisory lock blocks overlapping room bookings; selected equipment/CSSD release rechecked before use. |
| D13 | clinical_icu_rounds | Dated manual observations/round notes, sign/amend and separate patient histories; explicit device assignment/release linked to admission with version/timestamps; one active assignment per asset; no device control. |
| D14 | clinical_pregnancies | Manual antenatal/delivery record, atomic newborn identity and mother–child reference, human verification/closure; replay preserves one child identity. |
| D15 | clinical_pediatrics | Raw dated measurements with units and history; explicit manual immunization records link item/lot; historical recording does not infer a dose or dispense inventory. |
| D16 | clinical_rehab | Signed rehab referral order → assessment/active plan → capacity-checked appointments → immutable session progress → review/completion; all scheduled sessions require progress before completion. |
| D17 | clinical_dental | Tooth/site finding and procedure plan across visits; review/schedule/perform/verify/close; performance creates exactly one charge linked to the correct procedure and encounter. |
| D18 | clinical_blood_requests | Manual review/reserve/compatibility evidence/release/administration trace; reservation uniqueness; release rechecks patient/request/unit revision, evidence hash, expiry and eligibility; no compatibility algorithm. |
| D19 | clinical_diets | Manual diet/allergy note and meal round; revise before preparation, human review, prepare/deliver/cancel; encounter+meal round uniqueness. |
| D20 | clinical_referrals | Select immutable document revision, review, local packet export and manually sourced response/closure; exported does not mean remotely received; document export permission required. |
| D21 | clinical_portal_requests | Server-linked patient subject; own published encounters/results/documents; appointment requests enter staff booking queue; document correction requests create a staff task and preserve the original document. |

## API and recovery

- `GET /api/v2/clinical/catalog` returns permission-filtered module form/action definitions.
- `GET|POST /api/v2/clinical/{Dxx}/records` lists or creates that module's typed record. Search accepts `q`; clinical context filters accept `patient_id` and `encounter_id`.
- `GET /api/v2/clinical/{Dxx}/records/{id}` returns details and immutable history. It includes domain children such as bed history, handover tasks, therapy appointments/progress, immunizations and device assignments.
- `POST /api/v2/clinical/{Dxx}/records/{id}/actions` accepts `action`, the displayed integer `version`, and only the fields for that action. Every mutation requires the current server session, `X-CSRF-Token` and `Idempotency-Key`.
- `GET /api/v2/clinical/catalog/{resource}` supplies scoped selectors for slots, beds, staff, orders' downstream records, items/lots, eligible CSSD cycles, equipment, scheduled therapy sessions and published documents. Financial cost fields are excluded from clinical item/lot selectors.
- Portal endpoints are `/clinical/portal/me`, `/clinical/portal/encounters` and `/clinical/portal/released-results`. They derive ownership from the session, not request parameters.
- Imaging files and referral exports use authorized `/clinical/D11/records/{id}/file` and `/clinical/D20/records/{id}/export` endpoints. Files have stable content-addressed keys and checksum verification.

On unknown network outcome, retry exactly the same operation/key/payload. A changed payload with the old key conflicts. Definitive version/transition/permission failures do not perform partial database writes. Reload the current record before starting a new intent. Shared patient scope is checked again before returning a cached create result.

## Actual verification

The final clinical run used a fresh PostgreSQL 18.6 instance, applied Alembic, and executed 25 HTTP/database tests. The suite checks that migrations supplied the tables and never creates missing tables itself. Evidence is in `evidence/fullsystem/clinical-tests.txt`, `clinical-execution.json` and `clinical-journeys.json`; the execution report records exact source hashes and command. The tests include real concurrent slot, room, bed and blood reservation attempts, permission/scope negatives, canceled/revised source orders, wrong medication lots, duplicate dispensing/administration/child creation, immutable clinical corrections, portal ownership and linked J02/J03/J04/J08/J10 paths.

Clinical module tests do not themselves prove browser behavior. Browser verification is reported separately. All clinical inputs and files in these tests are authored synthetic data. AI in J08 is the explicit mock provider; live DR/CAD, live model inference, external hospital/payer systems and clinical/product effectiveness remain separately NOT_RUN/NOT_CONNECTED.

Run from the package root with a PostgreSQL 18 binary directory:

```bash
python scripts/test_with_postgres.py --pg-bin /path/to/postgresql18/bin -- python scripts/run_pg_suite.py tests/fullsystem/test_clinical.py -q
```

Use the locked backend environment. `FILE_STORAGE_PROVIDER=local` and `FILE_STORAGE_ROOT` configure the development file store. Other storage providers fail explicitly until implemented and configured. Do not put files or identifiers from real patients into this synthetic development profile.
