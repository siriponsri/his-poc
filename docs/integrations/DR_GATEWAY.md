# HIS DR bridge implementation contract

Status: FROZEN FOR IMPLEMENTATION on feat/carebalance-dr-bridge, based on
published LabClear main0c003e7. This is a new bridge, not an extension of the
LabClear laboratory foreign keys or generic AI inference route. DR runtime and
public acceptance are NOT_RUN for HIS until separately evidenced.

Owner amendment 2026-11-14: [PUBLIC_CFP_INTAKE.md](PUBLIC_CFP_INTAKE.md)
supersedes the initial synthetic-only origin, PNG-only media and v1-only
consent wording below. PUBLIC provenance is immutable JSONB with explicit eye
evidence and a public-dataset:<canonical evidence SHA-256> reference. PUBLIC
source snapshot v2 includes that provenance; synthetic v1 remains unchanged.
PUBLIC requires transfer wording v2. The ten owner-renamed MMRDR files remain
on hold for laterality metadata, as explicitly requested by the owner.

## Source and authority

The independent derivative at C:/Users/User/Desktop/myProject/carebalance-dr-screening
implements carebalance.dr.v1 and the service audience carebalance-dr-his-poc.
Its docs/CAREBALANCE_BOUND_RECEIVER.md defines the full service protocol. New
DTO code is authored for CareBalance; do not copy the original licensed DR
backend into this published HIS repository. Original DR source/Git/runtime,
real images, live inference, paid resources and new signing privileges remain
excluded. LabClear runtime/schema remain intact.

Read/preparation is derived narrowly from current effective D11 permissions,
documents.content/documents.export and current patient/visit access. Active
review task/visit and D11.write are additionally required for preparation.
dr.grade.confirm and dr.report.sign need explicit, current, verified,
facility-scoped grants. Generic clinician/imaging/admin, clinical.approve and
orders.sign are not DR signing credentials. Existing credential_allows alone is
insufficient because missing StaffMember currently returns true. Do not change
that generic credential path or broaden existing role permissions.

Grant records default empty. No public grant-creation endpoint is included in
this milestone. Isolated test fixtures may declare synthetic verified grants
to prove signing; public test01 remains unable to sign without a real separately
verified grant. Resolve grant identity/version fresh and include it in the
DR-specific authorization hash. Recheck after each external operation.

## New PostgreSQL evidence

Add migration0004_dr_screening_bridge without editing0003. Dedicated primary
models/tables plus an immutable grant lifecycle log:

1. dr_source_provenance: immutable authored-synthetic registration for exact
   D11 record/version/file hash and scope, generation/evidence reference,
   explicit laterality/modality/capture time, registrar/time. Registration is
   server-side from known authored fixtures; an upload/checkbox is not proof.
2. dr_source_sets: immutable patient/visit/dr_screening_review task, ordered
   manifest/revision/hash and provisioned receiver/workspace identity.
3. dr_source_set_items: ordered relational source links, exact D11 snapshot and
   hash, provenance reference and explicit eye/modality. Retain original orders.
4. dr_capability_grants: scoped user/capability/status/validity/verification
   evidence/verifier/version, default none.
5. dr_bindings: source set, actor/session and immutable explicit transfer-consent
   receipt bound to exact manifest hash/destination/purpose/wording/time.
6. dr_attempts: stable request/key/body/hash, DR authorization hash, lease,
   operation/state and response. Never repurpose LabClear attempts.
7. dr_exchanges: append-only actual transport outcome/receipt/quarantine.
8. dr_report_receipts: immutable report JSON/hash, source set and case/report
   revision/state, reviewer/signer/amendment provenance.
9. dr_capability_grant_events: append-only exact grant old/new snapshots, operation,
   time and actual database principal for offline operator changes. A DB trigger
   records lifecycle changes; do not invent an HIS user for direct SQL operations.

Composite encounter/patient/org/facility FKs, unique source positions and
source/version constraints are mandatory. Source/binding/confirmed receipts
cannot be retargeted. Evidence triggers reject deletion/rewriting. Grants may
be revoked or versioned with a durable audit history, never client-modified.
No startup seeding/reset and no HIS SQLite fallback.
Final grant resolution locks active grant rows in a stable order through commit;
an offline revocation cannot interleave between the final authorization read and
authoritative finalization. Expired/unreplaced leases cannot finalize success:
retain the actual exchange and quarantine it without enabling a new-key bypass.

## Source selection and consent

A dedicated D11 task kind dr_screening_review owns the selected1..8 sources.
Do not require completed acquisition order tasks to be open or equal to it.
Every source remains linked to its own checked current ClinicalOrder. Initial
source statuses are released/corrected, with exact immutable event/source
snapshot and existing content-read permissions. Require a current registered
authored-synthetic receipt. Laterality/capture/origin cannot be parsed from
body_site or inferred merely from PNG type.

HIS source snapshot is canonical JSON with schema=carebalance.his-dr-source.v1,
domain=D11, id, organization_id, facility_id, patient_id, encounter_id, order_id,
order_version, version, status, modality, body_site, file_sha256 and file_mime.
Exclude private file_path. Preserve strings exactly. source_sha256 hashes this
snapshot; image_sha256 hashes exact PNG bytes, read through file_store().read
with its symlink/path/checksum guards. Every source is<=1MiB;1..8 ordered images
must be fully decoded and dimension-checked by the receiver too.

Wire source manifest exactly matches the receiver's SourceManifest:
source_id/source_version/source_sha256/image_sha256/byte_size/media_type,
laterality L|R, modality CFP|UWF, source_origin SYNTHETIC, consent_reference,
capture_time UTC-Z|null. Hash the ordered manifest array excluding image_base64
using UTF8 sorted-key compact JSON, ensure_ascii=False, allow_nan=False.

Transfer requires explicit consent to exact sources, destination identity and
purpose. Destination selection is not source transfer or model consent. No
model operation is exposed. Authored synthetic origin does not establish
gradable quality: preserve explicit admission/quality review and Confirm Image.

## Receiver provisioning

One receiver process owns one immutable configured clinical scope/workspace.
Never reconfigure a running receiver from a request or switch global stores.
Use a server-owned destination registry mapping exact source-set scope to a
literal loopback IP/explicit port, expected workspace and dedicated key. No
browser URL/host/port/configuration. Unprovisioned source sets return an honest
unavailable state. Initial dedicated POC can provision one authored source set;
other patients must be denied rather than sharing that workspace.

All service messages use a fresh signed envelope, bounded body/response, UTC
expiry and audience, permanent receiver nonce protection, no redirect or env
proxy/cookies/identity header forwarding. Import/dispatch return ClinicalEnvelope
with exact request/binding/workspace, HTTP representation bytes/hash; read-report
returns the immutable report receipt. Sender validates all shapes/hashes/scope,
never treats malformed200 as success. Use the exact reviewed DTO contract;
copy only new protocol code if needed, record hash/provenance, and do not diverge.

Reserve durable attempts then commit/close before HTTP. Record actual exchange
before final authorization checks; quarantine stale/revoked/source races.
At signing the receiver persists an immutable all-source clinical review witness
with the signed report, after durable workspace reservation and a fresh complete
guard. Historical signature is retained. read-report exposes a separate typed
review_freshness {state:CURRENT|CHANGED|UNAVAILABLE,witness_sha256:null|string,
current_witness_sha256:null|string,checked_at,changed_case_ids}. HIS validates
the witness/source/report binding and displays historical signed evidence apart
from current review freshness; later grade changes must not silently appear
current. Assessment timestamps do not alter the immutable report hash. Unsigned
reports/missing historical witness return UNAVAILABLE, never CURRENT; CURRENT
requires non-null equal stored/current canonical witness hashes. Every case
witness source_sha256 is the HIS source snapshot hash from the sealed manifest;
separate image_sha256 is its exact image-byte hash. The native DR case field
source_sha256 means image bytes and must not be confused with this wire field.
Validate both hashes against the selected source manifest.
Stable semantic command/key and fresh transport envelope for recovery. Receiver
UNKNOWN after post-write crash must never be automatically redispatched, and a
different key cannot bypass unresolved work. Read/report/recovery remain
explicit; do not infer success from a timeout or complete HIS tasks/referrals.

## HIS browser/API surfaces

Under /api/v2/integrations/dr:

- POST /source-sets: selected registered sources, review task and explicit
  source/destination consent; idempotency key required.
- GET /source-sets and /source-sets/{id}: current scoped availability.
- POST /source-sets/{id}/bindings: session-bound explicit import with stable key.
- GET /bindings/{id}: current context/capabilities and pending status.
- POST /bindings/{id}/read-report: exact immutable report snapshot.
- POST /bindings/{id}/recover: original durable command/status, no auto-replay.

Browser entry /integrations/dr/{binding}/app/; assets below
/integrations/dr/{binding}/assets/{path}; GET|POST|PUT clinical JSON/images below
/integrations/dr/{binding}/api/{clinical_path}; protected print route
/integrations/dr/{binding}/print/{case_id}. Every page/asset/API/image/print request
revalidates current user/session/membership/patient/visit/task/source set and
capabilities. Mutations require existing HIS CSRF. No static assets through the
generic unauthenticated SPA fallback. Register bridge before final catchall.

Path/method/query allowlists mirror receiver exactly, including bound case IDs
and comparison other_image_id. Reject encoded separators/traversal/duplicate or
unknown query keys and unknown methods. Browser identity/reviewer is not trusted;
HIS context comes only from current server identity. Use validated local asset
manifest/path containment, trusted relative prefix injection and relative Vite
asset base. The server-issued return_url preserves current patient_id,
encounter_id and optional first-bound-source record as opaque parameters on
exact /domains/D11; never accept a caller return URL. Browser validates query
keys/duplicates/IDs against the verified context, with fixed /domains/D11 on
authentication/configuration failure. Never inject keys, raw sources or patient
names in URLs. Preserve
no-store, nosniff, same-origin CSP and no iframe bypass.

Bound frontend must fail closed if auth/config/health is missing or malformed,
hide broad workspace/admin/model/dataset/account/source-picker/referral surfaces,
and use one trusted prefix helper for all APIs/resources/print. Preserve clinical
worklist, admission quality controls, image confirmation, original geometry,
annotations, grading/report and revision/stale rules. UI cannot promote generic
clinician to verified signer. Public signing is visibly unavailable without a
verified grant; no fake successful button.

## Qualification and ownership

Backend owns new dr_protocol/client/models/gateway/registration modules,
migration0004 and their tests; main/model_registry registration and readiness
change are coordinated. Frontend is separately owned by parent after backend
freeze. Do not modify original DR/LabClear, existing auth/AI or migration0003.
Export contracts only after runtime API/schema stabilizes; parent integrates
docs/coverage/deployment/source publication.

Required actual isolated PostgreSQL evidence: explicit synthetic provenance and
consent→exact multi-source import→quality/image confirmation→original-pixel
annotation→manual grade→prepared/signed report with declared synthetic grant;
cross-patient/visit/facility/eye/source/session/grant expiry/revocation/CSRF/replay/
stale-source/receipt negatives; postwrite UNKNOWN/recovery; source/result/task
preservation and0 model calls. Public acceptance separately proves current
HIS auth on page/assets/API/images/print, allowed test01 preparation, denied
unverified signing and actual recorded result. No clinical effectiveness claim.
