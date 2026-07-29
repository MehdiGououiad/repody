# IDP functional architecture (as-built)

Functional-first IDP slice on a three-agent platform. Fraud and Computer Use are
SKIPPED stubs with dedicated Taskiq queues for independent scaling (ADR 007).

**Principles:** small pure functions · explicit data contracts · composition ·
side effects only at thin adapters · errors as data where partial failure is normal.

Canonical map: [CONTEXT.md](../../CONTEXT.md) · Decision: [ADR 006](../adr/006-three-agent-functional-idp.md) ·
Queues: [ADR 007](../adr/007-staged-agent-queues-taskiq.md).

## Hot path (staged)

```
taskiq (pool extract|fast) → process_run (claim, stage idp)
      → execute_platform_run(agent_stage=idp)
      → execute_idp_run → compose_idp → persist
      → if more agents: outbox handoff → pool fraud|computer_use
      → final stage: complete_run
```

When fraud/CU flags are off, IDP completes in one stage (parity with pre-ADR-007).

## Layout (live)

```
agents/idp/
  contracts.py     frozen DTOs
  compose.py       pure plan + compose_idp
  run.py           execute_idp_run + IdpRunPorts
  adapters/
    mapping.py     ORM/snapshot → contracts
    extract.py     extract_one → extraction.pipeline
    validate.py    rules.runner + summarize
    persist.py     fields/rules + optional complete_run

agents/fraud/      SKIPPED execute_fraud
agents/computer_use/  SKIPPED execute_computer_use

runtime/
  contracts/       Result, AgentOutcome, AgentContext
  recipe.py        resolve_recipe + one-stage execute_platform_run
  pools.py         pool ↔ agent map
  agent_metadata.py  handoff metadata + PendingCompletion
  run/             RunStatus, enqueue DTOs, id helpers

app/run/
  lifecycle.py     entity + events + pure transitions
  commands.py      claim / complete / fail / finalize
  processor.py     claim (idp) / resume (later) + handoff / finalize
  handoff.py       reuse outbox row for next pool
  persistence.py · snapshot.py · progress.py · intake.py
```

## Ownership

| Concern | Module |
|---------|--------|
| Claim / complete / fail | `app/run/` |
| Recipe + stage dispatch | `runtime/recipe.py` |
| Extract + validate | `agents/idp/` |
| VLM bytes → fields | `extraction/` (behind `adapters/extract.py`) |
| Rule evaluation | `rules/` (behind `adapters/validate.py`) |
| Fraud / CU stubs | `agents/fraud/`, `agents/computer_use/` |

## Worker pools

| Pool | Agent |
|------|--------|
| `extract` / `fast` | IDP (document vs logic-only capacity) |
| `fraud` | Fraud |
| `computer_use` | Computer Use |

## Non-goals

- Temporal / Hatchet for this scaffold
- Deep class hierarchies / Agent base classes
- Renaming `extract` → `idp`
