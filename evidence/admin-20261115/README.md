# Admin console evidence

Frozen runtime source: `e2bf12dbe750e7f2674a82bc8e98f8916de8a18d`.
The [release report](../../docs/ADMIN_RELEASE_20261115.md) separates qualification,
production activation/account provisioning and protected-browser acceptance.

- [Local qualification](local-qualification.json):38actual disposable PG18.6
  cases,171mounted frontend checks,31unit checks and build/typecheck.
- [Initial runtime observation](initial-runtime-summary.json):read-only baseline,
  old image/worker and real table/file inventory; two unrelated research
  containers were added since the historical release and preserved.
- [Candidate build](actual-build-v3.json):selected immutable image only.
- [Candidate static qualification](actual-static-v4.json):all315frozen runtime
  source/dist inputs and20assets checked as UID/GID10001.
- [Isolated restore and account qualification](actual-isolated.json):a restored
  synthetic0005database in an isolated network, generated test-only credential,
  normal login/permissions, replay and public-password policy checks; test
  containers removed and production baseline unchanged.

These safe projections contain no account password, session credential, private
environment, database backup or clinical body. Failed build/static attempts
remain in the private operator evidence and are summarized in the release
report; only the explicitly identified passing candidate can be selected.
No new model generation or clinical-effectiveness claim belongs to this task.
