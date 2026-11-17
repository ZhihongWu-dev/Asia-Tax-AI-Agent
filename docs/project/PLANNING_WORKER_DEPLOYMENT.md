# Planning worker deployment

The web service queues durable planning runs. `render.yaml` now defines a separate
`taxrora-planning-worker` process with manual deployment, the same build command,
Python version, region and target branch as the web service. No hosted worker
has been provisioned or accepted yet. Applying this Blueprint creates a paid
standard worker; preparing the file does not provision it. The standard plan is
an initial capacity setting, not a demonstrated production sizing result.

Use the same reviewed Git commit and installed tax-engine release for the web
service and worker. Their captured rule/runtime fingerprints must match. Build
the application with the existing `scripts/render_build.sh` in the supported
Linux deployment environment before starting either service.

Configure these secrets through the hosting provider, never in Git:

- `FSIE_WEB_DATABASE_URL`, if configured on the web service, must point the worker
  at that same case/queue database. The checked-in Blueprint shares
  `FSIE_DATABASE_URL` from the web service and assumes no web-database override.
  If the deployed web service has that override, also configure the identical
  override on the worker before its first start; do not consume a different queue.
- `FSIE_LIBRARY_DATABASE_URL` must use the dedicated `taxrora_library_reader`
  login. Provision its explicit grants using `scripts/library_reader_role.sql`,
  then set its password through secret provisioning. This login reads legal
  sources and review metadata, not private cases or the job queue.

Queue schema deployment remains separate from process startup. Startup checks
every `planning_runs` column but never creates or migrates tables. The worker
also loads the cloud library/review snapshot before claiming any job. A missing
reader or denied connection fails startup without consuming job attempts.

Run the non-consuming check first:

```sh
python scripts/run_planning_worker.py --check
```

Exit zero means the queue schema and reader snapshot check succeeded. It does
not establish complete legal-source admission, a successful optimization,
worker recovery, provider availability or business acceptance. Nonzero exits
print a fixed failure code rather than connection credentials.

Start one long-running worker with:

```sh
python scripts/run_planning_worker.py
```

`--once` can claim and execute one job; it is not a health check. The default
policy polls every 2 seconds, leases for 60 seconds, allows 1800 seconds per
attempt and at most 3 attempts. Override with `FSIE_PLANNING_POLL_SECONDS`,
`FSIE_PLANNING_LEASE_SECONDS`, `FSIE_PLANNING_WALL_SECONDS` and
`FSIE_PLANNING_MAX_ATTEMPTS`. A host restart must allow graceful SIGTERM so
active child processes can be cancelled; lease recovery still guards crashes.

Before production acceptance, verify a submitted case reaches a complete
artifact through the deployed worker, a second account cannot read it, stale
case revisions cannot replace current results, and restart/cancellation keeps
the lease and artifact guarantees. Record the deployed commit and actual
provider results. The local fixture suite is not a substitute for those checks.

2026-11-18 evidence: the real `--check` subprocess completed with exit 0 against
the existing cloud queue and dedicated reader, without entering the polling
loop. The daemon, worker, executor and isolated-process regression suites passed
30 tests in 16.10 seconds. This does not mean a hosted worker was launched.

References: [Render background workers](https://render.com/docs/background-workers),
[official Blueprint fields](https://render.com/docs/blueprint-spec),
[Render-owned configuration reference](https://github.com/render-oss/skills/blob/main/skills/render-blueprints/references/field-reference.md).
These describe deployment wiring; no upstream code or dependency was adopted.
