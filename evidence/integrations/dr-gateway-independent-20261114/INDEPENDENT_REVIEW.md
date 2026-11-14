# Independent HIS DR gateway review

Decision: READY_FOR_INTEGRATION for the exact frozen backend below. No unresolved P1/P2 findings in the inspected specification or documented repository-standards scope. This is not deployment, public/browser acceptance, clinical effectiveness or model qualification.

Reviewer is separate from backend implementer. Read-only repository review; only disposable PostgreSQL clusters and TEMP review evidence/scripts were written. Parent/frontend edits are outside this review's ownership and source-integrity claim.

## Candidate and integrity

- Repository: C:/Users/User/Desktop/myProject/his-poc
- Branch: feat/carebalance-dr-bridge
- Base HEAD: 0c003e753a5e93520780beca55e16078c1e34229
- Candidate is uncommitted working-tree backend, identified by 11 exact SHA256 hashes in final-review.json, also matching evidence/integrations/dr-gateway-20261114/source-integrity-freeze.json.
- Gateway: 674b6e9815729a420e7cc3e351f0b32156af1c5de47134a0e9b04deafe08cb29
- Client: 333654ca5625a762ae670514b82c481087d62cdb2b2fcded9e6b85f96fffeb0c
- Core: 012ccb88c670c23211facf2f7cb6c8dd4d773dae3a29df2fd1a4317b4ae75d3e
- Shared protocol: 9601d4798163721f60fdf301ffbe3873a42ebfd1382cf323bc14e310beed0391
- Migration0004: 7e1d28902fd4274b2dc7b2181debce6a63cdf718ef4950397cab158d066b489b
- All11 runtime/test and8 protected auth/AI/LabClear/domain files matched before and after exact-final qualification and the supplemental security test. No claim about concurrently edited frontend files.

## Specification axis

Reviewed full docs/integrations/DR_GATEWAY.md; nine dedicated scoped PostgreSQL tables, composite foreign keys/triggers; empty verified capability grants with no generic-role signer conversion; authored synthetic source registration and sealed manifest/consent/destination; fresh actor/session/source/order/task/grant checks before and after external work; off-transaction external calls; durable attempts/leases/idempotency/unknown quarantine; literal-loopback signed and bounded protocol; source/image identity and report witness/freshness; scoped page/asset/API/image/print and CSRF; manifest/path/catchall safety; closed-task historical reads and session ownership.

Confirmed pre-fix observations were returned to implementer and corrected:

1. Self-consistent envelope could deliver a different PNG under a requested original image ID. Corrected route-specific MIME/case/list/manifest identity checks and original bytes SHA at dr_client.py:179.
2. Self-consistent signed witness with missing confirmation/grade or incomplete signer proof could appear CURRENT. Corrected positive review milestones, signer identity, source/form/laterality associations at dr_client.py:252 and329.
3. Grant revocation could commit after final authorization read but before HIS receipt commit. Corrected ordered grant/verifier row locks through commit at dr_core.py:50; immutable lifecycle history now captures real database principal and exact OLD/NEW snapshots without inventing a human actor.
4. Expired unreplaced lease could finalize successful work. Corrected lease expiry guard at dr_gateway.py:261; retains actual exchange in quarantine and blocks cross-session new-key bypass.
5. Verifier predicates now scope organization/active state before row lock. Grant-history permission and own-user predicates run before lookup at dr_gateway.py:310. Case revisions reject missing/string/boolean values.

No unresolved P1/P2 specification finding after exact revised-candidate qualification.

## Standards axis

No unresolved objective repository-invariant violation identified in inspected backend scope. Auth/AI/LabClear sources and0003 were preserved; new0004 performs explicit migration with no startup seeding/reset. Shared protocol remained byte-identical to the independently qualified derivative DTO; no191 licensed legacy backend files copied into HIS. Source remains uncommitted and must be recorded as working-tree qualification rather than immutable-commit approval.

## Actual verification

PASS final-qualified-suites.xml: 66 tests,0 failures/errors/skips; fresh disposable local PostgreSQL18.6. Includes actual two-process HIS/derivative receiver HTTP and distinct PostgreSQL stores for authored-synthetic manual workflow. This real HTTP claim applies only to the repository interop test, not every unit/adversarial test.

PASS final-independent-negatives.xml: 9 independent adversarial tests,0 failures/errors/skips; fresh actual HIS/PostgreSQL with signed MockTransport malformed receipts/race hooks. Proves wrong original/MIME/foreign case/list rejected, expired lease quarantined and new session fenced, grant revocation serialized plus immutable history, and self-consistent invalid signed CURRENT witnesses denied.

PASS history-scope.xml: 1 supplemental actual HIS/PostgreSQL test. D11-less owner sees identical403 for existing and absent grant IDs, verifying the final scope-before-lookup delta cannot reveal existence.

Commands, timestamps, exit codes and exact source before/after are in final-review.json and history-scope.json. Raw text and JUnit XML retained. Starlette/httpx deprecation warning was emitted; tests did not fail or skip.

Historical evidence retained honestly:

- pre-fix-proof.xml:3 tests PASS means three vulnerable behaviors were successfully reproduced on old6a86/777 source; not approval.
- invalid_witness_proof.json records old self-consistent false-CURRENT acceptance.
- fixed-review.json: aggregate FAIL because gateway892 changed to674 during the first otherwise66+9 passing run. Do not promote it as0-drift evidence.
- final-review.json supersedes that mixed-source run, with exact674 and0 drift.

## Limits and next owner action

NOT_RUN here: deployed migration/service/connector changes; actual his.ai-cie.com authentication and page/assets/API/images/print acceptance; public test01 preparation/denied-signing behavior; browser UX; live inference/model/clinical effectiveness. No clinical/model call was authorized or executed by this reviewer.

Parent may copy this entire TEMP evidence folder into the repository evidence area and reference final-review.json plus history-scope.json. Preserve older failure/reproduction records. Any runtime/test mutation after the recorded freeze requires bounded requalification against new hashes. Parent retains deployment/publication authority and frontend integration ownership.
