# ADR 001: Taskiq for async audit runs

**Status:** Accepted (supersedes Hatchet)  
**Date:** 2026-07-03  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Audit runs can take seconds to minutes (PDF render, Repody VLM inference, rule evaluation). The API must accept run requests quickly, survive process restarts, and scale extraction separately from fast logic-only work.

Repody previously used Hatchet (`hatchet-stack` / Hatchet Lite + `hatchet-sdk`). That added RabbitMQ, a separate Hatchet Postgres, gRPC tokens, and OpenShift-specific packaging glue for modest workflow value (one task: `process-audit-run`).

## Decision

Use **Taskiq** with **Redis Streams** (`taskiq-redis.RedisStreamBroker`) as the background job queue:

- One Redis stream queue per worker pool: `repody:audit:ocr` and `repody:audit:fast`
- API enqueues via `services/run_dispatch.py` after the Postgres dispatch outbox commits
- Workers run `python -m audit_workbench.taskiq.worker` (Taskiq CLI, async tasks)
- Durable dispatch replay remains in Postgres (`run_dispatch_outbox`)
- Redis (`AUDIT_REDIS_URL`) is already required for rate limits, SSE, and extraction cache

## Consequences

**Positive**

- Removes Hatchet engine, RabbitMQ, and Hatchet token lifecycle from the platform
- Reuses existing Redis; simpler Compose and Kubernetes profiles
- Native async Python workers with pool-specific concurrency (`AUDIT_WORKER_*_MAX_JOBS`)
- Redis Stream broker supports acknowledgements and recovery (production-safe vs list queue)

**Negative**

- No bundled workflow UI (run status remains in Postgres + SSE/polling)
- Queue depth observability is Redis/metrics-based, not a dedicated workflow dashboard
- Workers and API must share a reachable Redis

## Alternatives considered

| Option | Why not |
|--------|---------|
| Hatchet (previous) | Heavy infra for a single background task |
| Procrastinate | Postgres queue contention; Redis already present |
| Inline-only | Blocks API; no horizontal worker scale |
| Temporal | Overkill for current single-step audit job |

## References

- `backend/src/audit_workbench/taskiq/` — broker, tasks, worker
- `deploy/helm/repody/templates/workers.yaml` — worker Deployments
- [Taskiq guide](https://taskiq-python.github.io/guide/)
