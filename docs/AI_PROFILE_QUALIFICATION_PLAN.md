# Bounded live synthetic profile qualification

2026-11-14 root implementation decision, before enabling the new profiles.

The dedicated dr-train Typhoon route passed two separately reviewed neutral
infrastructure calls. CPU2:71.31s total,58.19s load,7 generated tokens in4.09s.
CPU6:46.98s total,33.06s load,7 generated tokens in4.35s. Both observed GPU0
placement and unloading. These are two neutral checks, not profile qualification
or a throughput benchmark; warmed caches confound a CPU comparison.

The originally proposed90s timeout does not establish practical profile capacity.
Root permits an explicit maximum300s timeout (default remains90s),6 generation
threads and one4096 context for bounded qualification. The v1.1 prompt requests
at most2 facts,1 supported gap and2 short draft sentences. Strict source/effect
validation remains unchanged. The model is never asked to diagnose or prescribe.

Initial trial budget: one direct call per each of the four profiles, maximum
4 calls,300s per call,512 output tokens per call. No automatic retry, model pull,
cloud fallback,8192 context, real patient data or research-service changes.
Inputs come from persisted role-authorized collectors in a disposable synthetic
PostgreSQL database. Each call records exact source/provider/schema/prompt hashes,
outcome, usage, elapsed time and GPU/clock/power telemetry. Unknown cost is null.

Fresh GPU0 headroom, no external GPU0 compute and an empty shared11434 model
inventory must precede each dispatch. This is point-in-time admission, not an
exclusive reservation. Preserve failures and ambiguous server outcomes; reconcile
before any later call. Verify keep_alive0 unload and existing-service/model-byte
preservation after every completed call. Stop on contention or unknown outcomes.

Qualification must validate exact facts/citations and the profile's intended
draft/follow-up proposal. A valid JSON response alone is insufficient. Enable only
explicitly qualified profiles after reviewed results. Then separately validate
the durable queue, permissions, human edit/apply, reload and watch through the
actual application. Direct qualification is not an API authorization bypass.

Production timeout/output limits remain a later release decision based on actual
profile results. No target response time or saved staff minutes is claimed here.
