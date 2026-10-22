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
2. **Pools:** `extract` / `fast` only. No reserved fraud or computer-use streams, env keys,
   or Helm worker templates. See the amendment.
3. **One stage per task.** IDP completes the Run itself. Durable dispatch stays in the
   Postgres outbox. A second agent, if one is ever required, re-adds its own pool then.
4. **As-built:** Recipe is **IDP-only**. API producers start brokers for `extract` / `fast` only.
5. **No workers-ready gate** for agents that do not exist.
6. **Stage-aware ops** — handoff updates `worker_pool` + `last_activity_at`; stale reap uses
   activity (not only `started_at`); outbox replay claims with `FOR UPDATE SKIP LOCKED`;
   later stages skip re-exec when `agentOutcomes` already recorded.

## Amendment (2026-08): reserved agents removed

Points 2–5 above described capacity reserved for Fraud and Computer Use agents
that were never built. Holding a queue map, an `AgentId` member, four env flags,
two Helm Deployments at `replicas: 0`, two Compose services and an unreachable
handoff path cost roughly 150 references across 28 files and made every reader
ask which parts were live.

The reservation is withdrawn. Removed: `AgentId.FRAUD` / `AgentId.COMPUTER_USE`,
`POOL_FRAUD` / `POOL_COMPUTER_USE`, `AUDIT_AGENT_FRAUD_*` and
`AUDIT_AGENT_COMPUTER_USE_*`, the `workerFraud` / `workerComputerUse` chart
values and templates, the matching Compose services, `app/run/handoff.py`, and
`next_agent_after` with the `next_agent` / `finalize_pending` fields on
`PlatformStageResult`, and the unread `pendingCompletion` resume
(`store_pending_completion` / `finalize_pending_completion`). IDP completes
the Run inside `persist_idp_outcome` before `record_agent_outcome`. A retry
that already has `agentOutcomes` skips re-extraction and does not look for a
deferred completion payload.

`schedule_next_agent_stage` was already dead: its `_LIVE_HANDOFF_TARGETS` set
was empty, so every call raised.

What is kept, because it costs nothing and is still the extension point:
`AgentId`, `resolve_recipe` with `DEFAULT_AGENT_ORDER`, the `agent_stage` column
on `run_dispatch_outbox`, and the outbox dispatch machinery IDP itself uses.

Points 1 and 6 stand. A future second agent re-adds its own enum member, pool,
worker and handoff step at that time, against real requirements.

## Consequences

**Positive**

- No reserved worker chart for an agent that does not exist
- No new control plane (Temporal/Hatchet)
- Outbox replay still covers transient Redis failures
- Multi-stage runs will not be killed by a single-stage stale timeout during handoff

**Tradeoffs**

- Recipe is a stage dispatcher, not an in-process loop
- Outbox remains one row per run (reuse on handoff); multi-row outbox deferred
- Intermediate agent outcomes stored in `run_metadata.agentOutcomes`
- A future agent is a new requirement with a named owner, not a reserved slot

## Non-goals

- Temporal / Celery migration
- Renaming `extract` → `idp`
- Restoring SKIPPED stub packages for Fraud / Computer Use

## References

- `runtime/recipe.py` — stage execution
- `app/run/processor.py` — claim, execute, and resume an already-recorded stage
- `taskiq/broker.py` — producers for the IDP pools (`extract` / `fast`)
- [ADR 006](./006-three-agent-functional-idp.md) · [CONTEXT.md](../../CONTEXT.md)
