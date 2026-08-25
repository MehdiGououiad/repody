# IDP functional architecture (as-built)

Functional-first IDP agent. It is the only agent in the recipe (ADR 007).

**Principles:** small pure functions · explicit data contracts · composition ·
side effects only at thin adapters · errors as data where partial failure is normal.

Canonical map: [CONTEXT.md](../../CONTEXT.md) · Decision: [ADR 006](../adr/006-three-agent-functional-idp.md) ·
Queues: [ADR 007](../adr/007-staged-agent-queues-taskiq.md).

## Hot path

```
taskiq (pool extract|fast) → process_run (claim, stage idp)
      → execute_platform_run(agent_stage=idp)
      → execute_idp_run → compose_idp → persist → complete_run
```

## Layout (live)

```
agents/idp/
  contracts.py     frozen DTOs
  compose.py       pure plan + compose_idp
  run.py           execute_idp_run + thin IdpRunPorts
  progress.py      UI progress / GPU cold-start labels
  adapters/
    mapping.py     ORM/snapshot → contracts (+ IdpExtractionMeta)
    extract.py     extract_one → extraction.pipeline
    validate.py    rules.runner + summarize
    persist.py     fields/rules + complete_run

runtime/
  contracts/       Result, AgentOutcome, AgentContext
  recipe.py        resolve_recipe + one-stage execute_platform_run
  pools.py         pool ↔ agent map
  agent_metadata.py  stage metadata + PendingCompletion
  run/             RunStatus, enqueue DTOs, id helpers

app/run/
  lifecycle.py     entity + events + pure transitions
  commands.py      claim / complete / fail / finalize
  processor.py     claim + finalize
  handoff.py       reserved for multi-agent handoff
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

## Worker pools

| Pool | Agent |
|------|--------|
| `extract` / `fast` | IDP (document vs logic-only capacity) |

## Non-goals

- Temporal / Hatchet for this scaffold
- Deep class hierarchies / Agent base classes
- Renaming `extract` → `idp`
