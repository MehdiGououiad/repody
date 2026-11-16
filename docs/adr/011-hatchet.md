# ADR 011: Hatchet runs the queue, its limits and the maintenance cron

Amends the queue parts of [ADR 004](./004-cloud-kubernetes-packaging.md) and
[ADR 009](./009-simple-backend.md).

## Context

Runs were queued with Taskiq on Redis Streams, and around the queue we kept our own code for
what a workflow engine does:

- a dispatch stamp, and a sweep that sent lost tasks again;
- a sweep that failed runs stuck `queued` or `running`, plus an endpoint and a button to run it on demand;
- a per-client rate limit (the `limits` library on Redis, answering 429);
- a separate scheduler process for the periodic maintenance task;
- Redis itself, also used for an extraction cache.

[Hatchet](https://docs.hatchet.run) does each of these natively, on Postgres, which we already run.

## Decision

Runs go through Hatchet ([`repody/worker.py`](../../backend/src/repody/worker.py)):

| Need | Before | Now (Hatchet) |
|---|---|---|
| Queue a run | Taskiq on Redis Streams | `process-run` workflow, triggered with the run id after the commit |
| Trigger failed | Run stayed `queued`; maintenance re-sent it | The run fails at once; the API answers 503 |
| Run too long / worker lost | Maintenance sweep; recover endpoint | `execution_timeout` (`AUDIT_RUN_TIMEOUT_MINUTES`) and the failure task |
| Waited too long for a worker | Maintenance sweep (1 h) | `schedule_timeout` (1 h) and the failure task |
| Per-client rate limit | `limits` on Redis, 429 | Dynamic rate limit keyed by client: extra runs wait |
| Fairness between clients | None | Round-robin concurrency per client (`AUDIT_RUNS_IN_PROGRESS_PER_CLIENT`) |
| Stop a run | Mark it failed | Mark it failed and cancel its Hatchet run (`runs.task_run_id`) |
| Periodic maintenance | Taskiq scheduler process | A Hatchet cron (every minute) |
| Worker concurrency | `--max-async-tasks` | Worker slots (`AUDIT_WORKER_CONCURRENCY`) |
| Queue visibility | Logs | Hatchet's dashboard |

Removed: Redis, Taskiq, taskiq-redis, `limits`, the scheduler process, the extraction cache (audit
documents are rarely sent twice), `runs.dispatched_at`, the stuck-run sweep, `POST
/v1/operations/recover` and the "stale runs" counts.

What stays ours: every run status change still goes through `app/lifecycle.py`'s conditional
updates ([ADR 010](./010-explicit-lifecycles.md)). Hatchet delivers a task at least once, and
the claim makes a second delivery a no-op. The failure task only fails a run that is not finished.

Deployment: Hatchet Lite (one container, its queue in a `hatchet` database on our Postgres) in
Compose, locally and on the VPS. On Kubernetes, Hatchet's own Helm chart or Hatchet Cloud, as an
external service like Postgres. The client is `hatchet-sdk` 1.x, written against the APIs that
2.0 keeps (timedelta durations, `aio_create`, no deprecated calls).

Not adopted, because the workload doesn't need them: durable tasks (a run is one short task),
bulk fan-out, priorities, idempotency keys, and Hatchet's streaming (progress is in Postgres and
the UI polls it).

## Consequences

- A client over its per-minute limit no longer gets 429: its runs wait their turn.
- One fewer data store and one fewer process. Hatchet keeps 7 days of its own run history on the VPS
  (`SERVER_LIMITS_DEFAULT_TENANT_RETENTION_PERIOD`); our runs table is the record.
- The API and workers need a Hatchet API token: `pnpm platform` creates it locally, and the
  `hatchet-token` service on the VPS. On Kubernetes it goes in the runtime Secret.
- Tests run each run inline, without Hatchet. A real engine is exercised by the local stack.
- Started clean: the 1.0 schema migration was edited in place (`runs.task_run_id`), so an
  existing database is recreated, not migrated.
