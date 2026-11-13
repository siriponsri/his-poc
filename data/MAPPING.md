# Data → frontend mapping

## Implemented authored fixture mapping

Input format = project JSON schema 1.0; output format = read-only frontend view model. **ไม่ใช่ FHIR**, ไม่มี code system หรือหน่วยทางคลินิก.

| Source field | Frontend field/use | Rules |
|---|---|---|
| fixture_id | stable selection key | TH-001…TH-018; never an API patient ID |
| label / description | Thai scenario title / explanation | invented scenario text, not patient findings |
| patient_id / encounter_id | fixture context labels | prefix fixture-; never sent to mutation API |
| document.text | read-only document content | preserve empty string and multiline Thai text |
| document.author | optional evidence value | absent = missing, do not fill default silently |
| document.signed_at | optional display timestamp | fixed synthetic UTC ISO8601; not a clinical digital signature |
| expected_state | UI demonstration state | scenario, not persisted backend enum or measured outcome |
| data_classification | mode badge | WHOLLY_SYNTHETIC |
| source_id / asset_id | provenance link | manifest identifiers |
| api_response_fixture_ref | optional named frozen response | currently null; record fixture does not fabricate HTTP response |

No transformation to age, diagnosis, allergy, risk score, lab value or financial amount occurs. No fields are inferred from IDs. The frontend adapter owns parsing of actual v1 JSON-string columns and uses the separate frozen API contract fixture.

## External Synthea mapping specification — NOT_IMPLEMENTED

Candidate artifact URL is explicitly named FHIR R4, but actual `fhir_version` remains UNKNOWN until artifact metadata is inspected. No claim of 4.0.1 validation is made. Proposed mapping only:

| Source candidate | Planned view field | Verification before implementing |
|---|---|---|
| Patient.id | external source identifier | assigning authority + uniqueness; never substitute for p-demo |
| Patient.name | synthetic display name | retain source exact values; no Thai localization as genuine source |
| Encounter.subject.reference | encounter → patient link | resolve references and reject orphan/cross-patient linkage |
| DocumentReference/DiagnosticReport | staged evidence reference | resource availability, code systems, units, provenance and restrictions |
| Bundle.meta / exporter metadata | version/source lineage | inspect actual export and generator provenance |

Unsupported: clinical inference, FHIR server writes, medication/order/claim posting, terminology remapping, patient merge, birthdate-to-age assumptions, and backend import. No CSV→FHIR transformation performed. No external input checksum or derived output exists yet.
