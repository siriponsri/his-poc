# ERP workflows in the development prototype

The local application exposes typed, authorized endpoints under `/api/v2/erp`. `/erp/catalog` describes semantic form fields/actions for the React renderer. DTO schemas are exported in `contracts/v2/erp-inputs.json`; the OpenAPI operations also carry the concrete Pydantic types. Catalog data does not authorize a request. Services revalidate the session, check permissions and scope, serialize on records, enforce versions, and store operation responses in the same transaction as business effects and audit.

## Workspaces

| Domain | Primary records | Supporting workflow |
|---|---|---|
| D23 | Invoice open → priced → reviewed → invoiced; adjustments remain separate | Versioned price catalog, coverage evidence, source-bound charges, draft-only repricing |
| D24 | Claim draft → validated → exported → simulated_submitted → adjudicated → reconciliation_reviewed | Invoice/charge linkage, explicit synthetic aggregate remittance, local JSON export checksum |
| D25 | Receipt draft → reviewed → posted; separate requested/approved/refunded records | Independent refund approval, allocation policy, balanced journals and reversal entries |
| D26 | Cost draft → reviewed → posted; reversal is a negative entry | Department budget versions/review/post/reverse, UTC period variance, manual allocation method version |
| D27 | Request → approval by another actor → PO recorded → partial/full receipts → invoice verified → closed | Supplier catalog, lot movements and supplier obligation in the same transaction |
| D28 | Draft movement → validation → immutable posted movement | Item/lot/location catalog, reservation/consumption, transfer, quarantine return, independent count approval |
| D29 | Register → service → maintenance due → maintenance → verified → release | Work order, manual evidence and verifier; clinical resources recheck asset availability |
| D30 | Roster draft → reviewed → published → acknowledgment by assigned staff | Overlap checks, staff credential privilege, revoke/restore; staff cannot publish other rosters |
| D31 | Separate CSSD, linen and facility work orders | Manual cycle evidence/release, quarantine blocks release; independent linen and repair states |
| D32 | Incident → triage → investigation → CAPA → effectiveness review → closed | Restricted reporter identity, owner evidence and independent effectiveness reviewer |
| D33 | Report draft → generated → reviewed → exported; corrections create new batches | Defined local mapping, source lineage, local/manual receipt evidence and JSON export checksum |
| D35 | Inbox received → validated/rejected → queued → local delivery/failure → local acknowledgment | Durable attempts, unique receipt and reconciliation task; duplicate source delivery does not repeat effect |
| D36 | Cohort draft → previewed → approved → frozen → exported/revoked | Allowlisted encounter-kind filter, immutable row snapshots/patient splits, explicit dataset grants and download checks |

## Financial meaning

`billed` is the invoice's issued total and does not change when the price catalog changes. `submitted` and `approved` come from the claim and synthetic remittance. Importing approval does not create cash. `gross_received` retains original posted receipt amounts; `refunded` sums separate executed refunds; `net_received = gross_received - refunded`.

`outstanding = billed + signed invoice adjustments - payment allocations + explicitly released allocations`. A refund changes outstanding only when its reviewed `release_allocation` policy says to reopen that receivable. This choice is retained in the refund record. `cost` is recorded **encounter** cost, not an inferred profit or an allocation to each invoice. Budget variance uses departmental cost creation timestamps in UTC for the selected year or month and retains the operator's method version.

This local claim format is not a payer format. Aggregate adjudication is manually entered for the synthetic claim; per-payer rules/certification and line-level payer adjudication formats remain external integration work. No receipt or refund calls a bank or payment gateway.

## Inventory meaning

A signed immutable movement is the stock ledger. Positive return quantities require a matching original negative movement, and cumulative returns cannot exceed that issue. Returned items default to quarantine; no automatic quality disposition occurs. Transfer writes an outgoing and incoming entry in one transaction. Reservations reduce unreserved availability; consumption creates exactly one linked movement. Posting a count rechecks the quantity observed at count creation and requires a different approver.

The schema guards posted stock facts, receipt financial facts, ledger entries/lines, invoice adjustments, receipts, remittance, report lineage and dataset rows. Journal balance is a deferred PostgreSQL constraint, so a partially written journal cannot commit. The authorizing organisation fence deliberately prioritizes consistent revocation and correctness over production throughput in this prototype.

## Exports and integrations

Report/claim JSON exports are explicit local formats with a checksum. Local report acknowledgment is labelled unverified externally. Dataset details expose metadata, not raw rows; raw download requires `D36.export`, a current per-dataset access grant, an allowed facility, and a non-revoked frozen/exported dataset. Revocation prevents future downloads and does not claim to recall files already downloaded.

No endpoint in these workflows transmits to external payer, warehouse, regulator, banking or sterilizer systems. Delivery to `local_explicit_stub` creates a local receipt and reconciliation task only. All records generated by the release tests and seed are synthetic.

## Evidence

`tests/fullsystem/test_erp.py` runs actual PostgreSQL API behavior and concurrent stock issuance through separate clients. `evidence/fullsystem/erp-tests.txt` contains the latest run output; `erp-journeys.json` records J05/J06/J09 actors and IDs. Browser and external integrations must be assessed separately in the release validation report; this document is not a PASS assertion.
