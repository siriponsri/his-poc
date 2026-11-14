# Source-bound generation grammar and dispatch observations

The first real v1.1 visit attempt remains invalid and unchanged. Its55.584s
response omitted gap evidence, referenced document `field=text` and omitted the
draft effect's ID binding. No other profile was called after that rejection.

The v1.2 grammar now uses only each included source's real field keys or its
quotation branch, supported typed workflow gaps and offered effect IDs. Draft
effects require their actual draft_id. The model cannot supply display/gap-title
fields; the server constructs these from verified source data. Independent
post-generation validation remains unchanged and still rejects the old result.

PASS:62 disposable-PG integration/provider checks before dispatch-observation
metadata, including four actual collectors→provider/schema→worker paths with
explicit HTTP doubles. PASS:58 focused/new+legacy provider checks after metadata,
including malformed chat versus preflight failure. No real model calls in these
checks. See `provider-integration-v12.json`; raw root XML remains private.

Both adapters record dispatch_started before the chat request and record
terminal_response_observed only after a hashed JSON response identifies the
pinned model and done=true. This establishes physical completion only; invalid
or source-stale content remains unusable. Backend quarantine must consume these
trusted observations with an immutable audit binding before production enablement.

New v1.2 live qualification and production deployment remain NOT_RUN here.
The separately pinned continuation must retain the earlier failed attempt.
