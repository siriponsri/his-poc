# Current workflows and acceptance

Canonical minimum semantics are in `../spec/DOMAIN_IMPLEMENTATION_MATRIX.md`; current routes/services/states/evidence in `../DOMAIN_COVERAGE.json`. Shared state machines validate expected version and allowed transition at backend; field renderers do not decide authorization.

J01 registration → appointment/queue → OPD → immutable document → explicit mock run → proposal/edit/review → persisted result/audit uses one patient/encounter/task chain. Approval binds proposal version/hash and exact evidence/task snapshot. Edits return pending with new version; stale evidence or revoked signer prevents commit. Failed/timeout/invalid/abstain runs remain visible without a proposal.

J02 manual lab specimen/result/release/correction/acknowledgment. J03 reviewed medication order → eligible lot → atomic dispense/stock/charge; returns reference original and stay quarantined until explicit disposition. J04 emergency/admission → non-overlapping bed allocation → transfer/handover → discharge/follow-up. Human-entered clinical fields do not represent automatic clinical recommendations.

J05 charges/invoice/claim → local synthetic remittance → receipt/refund → reconciliation/cost. Receipt does not arise from claim approval. Example expected: billed1000, approved800, gross_received800, refunded100, net_received700; cost300 separately. Outstanding derives from billed+adjustments−allocated+explicit released allocation. Refund is its own immutable cash record, not an overwrite of original receipt. Posted journals balance; reversal appends opposite entry.

J06 purchase approval → partial/full goods receipt → stock/AP; duplicate receipt/issue keys cannot duplicate movement. J07 identity/membership/scope/revoke → direct denied API → bounded audit. J08 image checksum/study/manual report → mock review task → versioned referral packet; export never means a remote hospital received it. J09 asset/staff/support/CAPA → source-linked operational report. J10 portal subject sees only released own data and staff receives the same appointment request.

Each journey has independent execution status in `../JOURNEY_COVERAGE.md`. L2/L3 must be supported by actual PG/browser evidence, not by this narrative. External payer/LIS/PACS/models remain NOT_CONNECTED/NOT_CONFIGURED until their own adapter verification is performed.
