# Guarded assistant worker templates

These templates default to disabled, unbound and unqualified. Installing them
does not start the worker, enable a user service, provision a database ENV or
make an inference call. Model qualification is source-fidelity evidence on one
authored fixture per profile, not clinical validation or workload acceptance.

The supervisor surrounds the real `backend.app.assistant_worker --once` CLI.
Each CLI invocation scans eligible watches and prepares at most one queued run.
The backend still revalidates actor/session/scope/source and uses the PostgreSQL
admission fence shared with legacy D37. A TTL expiry or empty provider queue
cannot clear sticky unknown execution: a bound positive terminal/no-dispatch
audit marker or a separately authorized audited operator reconciliation is
required. This host wrapper never edits that evidence or a database.

Before every one-shot, then again under the pause/dispatch lock immediately
before launch, the host checks the exact active HIS app name, compose project,
service, immutable candidate image and current running/healthy state. A fallback,
changed app or unhealthy app blocks dispatch. It then checks pinned engine/container/runtime projection and
model identity, GPU0 >=10000MiB free, no GPU0 compute process, and empty dedicated
and legacy model residency. This is a point-in-time check, not an exclusive GPU
reservation. Busy or unknown metadata dispatches nothing. Other GPUs, models,
services and research jobs are never stopped or changed.

Worker image/ENV SHA, runtime projection, endpoints, GPU UUID and reviewed
profiles must be explicitly bound later. The worker uses an immutable local
image (`--pull=never`), read-only root, no GPU device,1CPU/1GiB/128PIDs. The private
ENV must live beneath the guarded state directory and be0600. No ENV or database
URL is supplied in these templates. Docker access grants host authority; this
is not a security sandbox.

The supervisor uses one Linux flock singleton and an atomic pause/launch lock.
Deadline, nonzero result or ambiguous post-dispatch error creates an immutable
HALTED_UNKNOWN marker, with no automatic retry/restart/model kill. On the480s
deadline the bounded stdout reader remains alive until the existing CLI exits,
while new dispatch is fenced; it does not close a live worker's output pipe to
manufacture quiescence. A retained HALTED_UNKNOWN prevents every later start.

The private ledger rotates at1MiB with four older copies; current/older worker
output tails are capped at256KiB with twelve older copies. Rotation touches only
those named disposable diagnostic files. Halt markers, raw clinical/AI evidence
and database audit are never rotated or cleared. Logs remain private and may
contain worker error output. The optional user unit bounds CPU25%,RAM256MiB and
64tasks, but is not the selected persistence path. The cron supervisor's bounded
buffers/logs do not establish an OS memory/CPU quota. Its host resource usage
must be measured at later activation; the worker container retains explicit
1CPU/1GiB/128PID limits. The enabled sentinel is absent by default.

`control.py pause` only fences new dispatch under the same lock. `status` reports
the named worker, pause/enable/halt metadata and explicitly does not prove DB
admission or model drain. There is no resume, retry, enable, marker-clear or
database reconciliation command here.

Before rollback, pause, retain unknown markers, wait for the named worker/CLI
to exit, independently prove both model endpoints drained and zero GPU0 compute,
and inspect the backend admission predicates for no active reservations/holds
or sticky unknown quarantines. Neither wall-clock expiry nor `ps[]` alone is
sufficient. Keep queued work/watches/revisions/approvals/effects/audit unchanged.
Only then may a separately qualified old-behavior0005-compatible app be selected.

Installation, a dated one-off disabled cron verification, cleanup and activation
require separate hash-bound root gates. Selected persistence is a named user
`@reboot` block, preserving all old crontab bytes. Its foreground launcher has no
periodic restart. Initial verification needs a private exclusive root request
and token, records actual cron ancestry/PID/cgroup, and makes zero Docker/HTTP/DB
calls. Remove only the exact owned one-off line after a fresh full-byte compare;
unknown crontab changes stop cleanup. There is no native crontab compare-and-swap
API: installation requires a quiet operator window plus before/after byte proof.

The boot path does nothing while paused/disabled/ACTIVE/HALTED. Runtime start
requires a separate enabled approval binding the actual config. No source ENV,
database URL, root token or preexisting crontab contents is supplied here. No
linger, root unit, global service, or unrelated cron change is required. A user
manager exists but Linger=no, so the optional unit cannot establish logout
persistence. Runtime binding and actual foreground cron persistence after SSH
disconnect still need later validation.

The host observes process/metadata failures only. Current backend CLI returns0
without a provider-state summary: provider-unknown inference is quarantined by
durable backend audit-bound global admission. The host may continue watch or
capacity scans, but that backend fence prohibits new inference. This release
accepts that division; the host still HALTs on its own deadline, nonzero exit,
ambiguous dispatch or ACTIVE marker surviving a process restart. No CLI change
or candidate source change is required.
