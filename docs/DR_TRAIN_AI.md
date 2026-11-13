# Optional private Typhoon document review

The default application uses `HIS_AI_PROVIDER=mock_demo`. This guide describes the separately authorized `dr_train_ollama` route for **authored synthetic document completeness only**. It uses an existing dr-train installation through private SSH forwarding. It does not download models, train them, enable a public inference service, or authorize real patient data.

## Verified scope and identity

The observed Ollama runtime is **0.12.6**. Hardware inventory includes a Tesla V100-SXM2-32GB and an RTX 2080 Ti; the verified inference work used the existing V100-backed route. Installed model metadata, runtime declarations, and executed inference results remain distinct.

| Artifact | Installed identity | Executed scope |
|---|---|---|
| Typhoon | `hf.co/scb10x/typhoon2.1-gemma3-12b-gguf:Q4_K_M` | Three synthetic Thai checklist cases and one rendered human-review workflow |
| MedGemma | `hf.co/unsloth/medgemma-27b-text-it-GGUF:Q4_K_M` | Installed/inventoried; inference NOT_RUN |

Typhoon's expected Ollama manifest digest is:

```text
ab914ef406c9a78e2a8893eaa3b0ef78049f6c4e2703626433028e838d3a168b
```

The observed chat-template SHA-256 is `109037bec39c0becc8221222ae23557559bc594290945a2c4221ab4f303b8871`. Runs record template, parameters, prompt, schema, input, response, and installed-model provenance. The upstream Hugging Face revision is **UNKNOWN**; the installed Ollama manifest digest is the enforced artifact pin. A model tag or its `Q4_K_M` suffix alone is not a verified upstream revision or performance claim.

The earlier [inventory snapshot](../evidence/fullsystem/live-ai/dr-train-inventory.json) records both models as inference NOT_RUN at that observation time. Later [real provider cases](../evidence/fullsystem/live-ai/real-provider-cases.json) establish the bounded Typhoon result; they do not upgrade MedGemma.

## Configure the optional profile

Prerequisites are a configured owner SSH alias with an already trusted host key, non-interactive authentication, the existing authorized Ollama service, and Python dependencies from `requirements-backend.txt`. Keep SSH addresses and keys in your private SSH configuration. The SSH target below is a placeholder, not a repository-provided connection.

Edit the private project `.env` using [.env.example](../.env.example):

```dotenv
HIS_AI_PROVIDER=dr_train_ollama
HIS_LIVE_SYNTHETIC_ENABLED=true
DR_TRAIN_TUNNEL_ENABLED=true
DR_TRAIN_SSH_TARGET=YOUR_CONFIGURED_SSH_ALIAS
DR_TRAIN_BASE_URL=http://127.0.0.1:18134
DR_TRAIN_MODEL=hf.co/scb10x/typhoon2.1-gemma3-12b-gguf:Q4_K_M
DR_TRAIN_MODEL_DIGEST=ab914ef406c9a78e2a8893eaa3b0ef78049f6c4e2703626433028e838d3a168b
DR_TRAIN_OLLAMA_VERSION=0.12.6
DR_TRAIN_TIMEOUT_SECONDS=180
DR_TRAIN_MAX_OUTPUT_TOKENS=1024
DR_TRAIN_CONTEXT_TOKENS=8192
DR_TRAIN_MAX_DOCUMENT_CHARS=6000
DR_TRAIN_KEEP_ALIVE_SECONDS=0
```

Choose the base URL from the application's location:

| Application location | `DR_TRAIN_BASE_URL` |
|---|---|
| Native Python on the owner's machine | `http://127.0.0.1:18134` |
| Docker Desktop application container | `http://host.docker.internal:18134` |

The tunnel helper runs on the owner's machine and binds `127.0.0.1:18134`, forwarding to the remote service's loopback port 11434. Docker's `127.0.0.1` refers to its own container, so it needs the host route instead. Linux Docker host routing requires separate configuration and is not established by the Windows Docker Desktop result. Do not copy the remote address or SSH credentials into Compose or frontend code.

Helper defaults are local port 18134, remote port 11434, and SSH port 22. Explicit optional overrides are `DR_TRAIN_TUNNEL_LOCAL_PORT`, `DR_TRAIN_REMOTE_PORT`, and `DR_TRAIN_SSH_PORT`; update the application base URL consistently if the local port changes. This guide's selected context is 8192. Set it explicitly: the provider and Compose fallback for an absent setting is 4096.

From the project root:

```powershell
python -m pip install -r requirements-backend.txt
python scripts/dr_train_tunnel.py start
python scripts/dr_train_tunnel.py status
python scripts/dev.py start
```

`start` and `status` on the tunnel helper read `/api/version` and `/api/tags` and require the exact configured engine/model/digest. They do not request inference or pull a model. A matching existing listener is verified and reused without assuming process ownership. Private process metadata/logs stay under ignored `var/dr-train/`; a saved PID is never treated as authority to terminate a process. SSH uses batch mode and strict host-key checking, so configure access and trust before running it.

`dev.py up`, `start`, and `native-up` perform the tunnel preflight automatically only when both the provider and tunnel opt-in select it. `start` and `native-up` retain their non-seeding behavior. A preflight failure stops application startup. Shell/process environment values take precedence over `.env`; stale exported settings can override a corrected file.

To return deliberately to the default profile, set `HIS_AI_PROVIDER=mock_demo`, `HIS_LIVE_SYNTHETIC_ENABLED=false`, and `DR_TRAIN_TUNNEL_ENABLED=false`, then restart through the launcher. This explicit operator change is separate from fallback: a failing live request never switches provider automatically. The helper has no blanket stop command for pre-existing SSH listeners.

## Use the five-section review

1. Sign in as an authorized clinical user with server-side care assignment. Select the patient and encounter.
2. Save an authored synthetic document in D22 and create/select its D37 `document_review` task. Live mode accepts this task kind only; mock scenario selection is unavailable.
3. In D37, select the task and saved document and request a proposal. The backend sends the bound document revision through the configured route.
4. Inspect the five fixed findings: chief complaint/reason, history/context, author-recorded assessment, author-recorded plan/follow-up, and author identity. Each is `present`, `missing`, or `unclear`. A present finding needs a nonempty exact source quote; a missing finding cannot cite one. Output with invented quotes, duplicate/missing keys, unsupported fields, or incomplete generation is rejected.
5. Read the original evidence. Edit the proposal summary if needed; that creates a new version while retaining the model checklist. Approve the displayed version, then commit it. Approval, action hash, source revision, encounter/task state, reviewer authority, and current scope are checked again before the atomic result/audit/idempotency write.

The model checks documentation presence. It does not assess diagnosis, treatment, dose, triage, blood compatibility, or whether the author's clinical assessment is correct. One finding marked present is not an endorsement of its content.

## Limits and failure behavior

| Setting or guard | Current behavior |
|---|---|
| Document/title | Default document cap 6000 characters, configurable up to 8000; title up to 200 characters |
| Context | Supported configured range 2048–8192; the verified checklist profile uses 8192 |
| Conservative input guard | UTF-8 bytes of system prompt + JSON input envelope, plus 512 reserved units and maximum output tokens, must fit the configured context budget |
| Output | 256–1536 maximum output tokens; this profile uses 1024; normalized checklist JSON is capped at 24,000 UTF-8 bytes |
| Timeout | One absolute transport deadline, configurable 5–300 seconds; profile uses 180 |
| Retention | `keep_alive` defaults to 0, configurable up to 60 seconds |
| Admission | One active live attempt per provider in the shared application database; competing requests record `LIVE_PROVIDER_BUSY` rather than silently queueing extra inference |

The byte guard is intentionally conservative, not an exact tokenizer. Thai characters often consume several UTF-8 bytes, so a document can be rejected by `DOCUMENT_CONTEXT_BUDGET_EXCEEDED` before reaching the character cap. The runtime's advertised larger context is not the application's accepted source budget. The adapter also checks reported prompt usage after inference.

Inference runs outside the database transaction. The backend first reserves a durable attempt, releases the transaction, performs the provider call, then rechecks permissions and all evidence/state bindings. Source edits, revocation, stale context, timeout, failure, abstention, or invalid output cannot become a successful proposal through fallback. A disconnected client retries the same operation key; it must not create a new request merely because the original response was lost. Interrupted attempts retain their recorded outcome and lease policy.

The adapter verifies engine/model identity before and after inference, refuses redirects/environment proxies, and accepts structured assistant text without tool calls. Unknown providers or missing pins fail closed. Transport cancellation is not proof that the remote server stopped generation; server-side cancellation remains unverified. Measured cost stays `null` when no monetary measurement exists.

## What was actually tested

| Evidence | Observed result |
|---|---|
| [Three real authored Thai cases](../evidence/fullsystem/live-ai/real-provider-cases.json) | Complete, missing-plan, and missing-author cases PASS; source quotes validated |
| [Actual real-model browser workflow](../apps/web/evidence/fullsystem/live-dr-train-final/browser-live-ai.json) | 7 assertions PASS, including human edit, approval, commit, reload, and provenance |
| [Read-only browser follow-up](../apps/web/evidence/fullsystem/live-dr-train-readback/browser-live-ai-readback.json) | 2 assertions PASS; same run/proposal/result, no new inference or domain mutation |
| [Orchestration regressions](../evidence/fullsystem/live-ai/final/live-orchestration-final.txt) | 17 PostgreSQL tests PASS with deterministic provider doubles; not real model inference |
| [Updated frontend checks](../evidence/dr-train/frontend-ui/execution.json) | 60 component tests PASS plus recorded unit/audit/typecheck/build results |

The real browser sample recorded 11.205 seconds, 408 prompt tokens and 141 generated tokens, with measured cost `null`. It is one observed request, not a throughput, latency, or accuracy benchmark. The pre-existing all-38 L2/all-10 L3 local acceptance used the mock profile; its 25 unit/53 component baseline remains historical evidence, not a rerun of all journeys with this model.

No additional model is required for this verified scope. Consider another model only for a named unmet task with its own authorized resources, license review, synthetic evaluation set, and acceptance criteria. Installed MedGemma can be evaluated later if that scope is approved; its availability alone supplies no benchmark, clinical capability, or integration result. Other model routes, external systems, real-data use, and clinical/product effectiveness remain NOT_RUN or unverified as recorded in coverage.
