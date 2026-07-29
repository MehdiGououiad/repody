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
2. **Pools:** `extract` / `fast` = IDP capacity classes (unchanged names); add `fraud` and
   `computer_use` streams (`repody:audit:{pool}`).
3. **Staged handoff:** each task runs **one** agent stage; on success, reuse
   `run_dispatch_outbox` row (`pool` + `agent_stage`, status `pending`) and
   `schedule_outbox_dispatch` for the next stage. Durable dispatch stays in Postgres.
4. **Flags default off** — `AUDIT_AGENT_FRAUD_ENABLED` /
   `AUDIT_AGENT_COMPUTER_USE_ENABLED` false → IDP completes in one stage (behavior parity).
5. **Workers-ready gate** — Fraud/CU enter the recipe only when
   `AUDIT_AGENT_*_WORKERS_READY=true` (Helm sets this from Deployment replicas / HPA min).
6. **SKIPPED stubs** live under `agents/fraud/` and `agents/computer_use/` until real logic.
7. **Stage-aware ops** — handoff updates `worker_pool` + `last_activity_at`; stale reap uses
   activity (not only `started_at`); outbox replay claims with `FOR UPDATE SKIP LOCKED`;
   later stages skip re-exec when `agentOutcomes` already recorded.

## Consequences

**Positive**

- Helm can scale `worker-fraud` / `worker-computer-use` independently of extract/fast
- No new control plane (Temporal/Hatchet)
- Outbox replay still covers transient Redis failures
- Multi-stage runs are not killed by a single-stage stale timeout during handoff
- Extract admission drops after IDP→fraud handoff (`worker_pool` update)

**Tradeoffs**

- Recipe is a stage dispatcher, not an in-process loop
- Outbox remains one row per run (reuse on handoff); multi-row outbox deferred
- Intermediate agent outcomes stored in `run_metadata.agentOutcomes`
- Enabling Fraud/CU requires both feature flag and workers-ready (or IDP stays solo)

## Non-goals

- Temporal / Celery migration
- Renaming `extract` → `idp`
- Real Fraud / Computer Use business logic

## References

- `runtime/recipe.py` — stage execution (returns `finalize_pending`; does not call `complete_run`)
- `app/run/finalize.py` — complete from `pendingCompletion` after final non-IDP stage
- `app/run/processor.py` — claim (IDP) vs resume (later stages) + handoff/finalize
- `taskiq/broker.py` — producers for all pools
- [docs/architecture/idp-functional-agents.md](../architecture/idp-functional-agents.md)
