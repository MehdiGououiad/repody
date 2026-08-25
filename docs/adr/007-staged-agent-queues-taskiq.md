# ADR 007: Staged agent queues on Taskiq

**Status:** Accepted  
**Date:** 2026-07-22  
**Context:** [CONTEXT.md](../../CONTEXT.md) · Supersedes in-process recipe loop in [ADR 006](./006-three-agent-functional-idp.md) · Keeps [ADR 001](./001-taskiq-async-runs.md)

## Context

Independent scaling of IDP / Fraud / Computer Use requires each agent to run on its own
worker pool. Running the full recipe inside one Taskiq task (IDP → Fraud → CU) holds a
single worker across all stages and prevents HPA per agent.

We already left Hatchet (ADR 001) because a heavy workflow engine was overkill. Temporal
remains optional later if mid-run resume / HITL / complex retries become production needs.

## Decision

1. **Keep Taskiq + Redis Streams** — one `RedisStreamBroker` per queue (`queue_name`),
   task registered on that broker, API `broker.startup()` before `kiq`, one worker process
   per pool ([Taskiq architecture](https://taskiq-python.github.io/guide/architecture-overview.html),
   [taskiq-redis](https://github.com/taskiq-python/taskiq-redis)).
2. **Pools:** `extract` / `fast` = IDP capacity classes (unchanged names); reserve `fraud` and
   `computer_use` stream names (`repody:audit:{pool}`) and Helm worker templates
   (`workerFraud` / `workerComputerUse`, values replicas 0) until real agents ship.
3. **Staged handoff (future):** when multi-agent recipes return, each task runs **one** agent
   stage; on success, reuse `run_dispatch_outbox` (`pool` + `agent_stage`, status `pending`)
   and `schedule_outbox_dispatch` for the next stage. Durable dispatch stays in Postgres.
4. **As-built (2026-08):** Recipe is **IDP-only**. Fraud / Computer Use agent packages and
   SKIPPED stubs were removed. `AgentId.FRAUD` / `COMPUTER_USE` and pool name maps remain
   for reserved Helm capacity; API producers start brokers for `extract` / `fast` only.
   Env keys `AUDIT_AGENT_FRAUD_*` / `AUDIT_AGENT_COMPUTER_USE_*` are reserved/inert (not
   consulted by `resolve_recipe`).
5. **Workers-ready gate (future)** — when Fraud/CU agents exist, enter the recipe only when
   both feature flag and `AUDIT_AGENT_*_WORKERS_READY=true` (Helm from Deployment replicas).
6. **Stage-aware ops** — handoff updates `worker_pool` + `last_activity_at`; stale reap uses
   activity (not only `started_at`); outbox replay claims with `FOR UPDATE SKIP LOCKED`;
   later stages skip re-exec when `agentOutcomes` already recorded.

## Consequences

**Positive**

- Helm keeps `worker-fraud` / `worker-computer-use` chart templates (values replicas 0) for future scale-out
- No new control plane (Temporal/Hatchet)
- Outbox replay still covers transient Redis failures
- Multi-stage runs will not be killed by a single-stage stale timeout during handoff

**Tradeoffs**

- Recipe is a stage dispatcher, not an in-process loop
- Outbox remains one row per run (reuse on handoff); multi-row outbox deferred
- Intermediate agent outcomes stored in `run_metadata.agentOutcomes`
- Enabling Fraud/CU later requires real agent packages, recipe wiring, flags, and workers-ready

## Non-goals

- Temporal / Celery migration
- Renaming `extract` → `idp`
- Restoring SKIPPED stub packages for Fraud / Computer Use

## References

- `runtime/recipe.py` — stage execution (returns `finalize_pending`; does not call `complete_run`)
- `app/run/commands.py` — `finalize_pending_completion` after a final non-IDP stage (future)
- `app/run/processor.py` — claim (IDP) vs resume (later stages) + handoff/finalize
- `taskiq/broker.py` — producers for live IDP pools (`extract` / `fast`)
- [docs/architecture/idp-functional-agents.md](../architecture/idp-functional-agents.md)
