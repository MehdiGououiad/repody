# ADR 006: Three-agent platform with functional IDP slice

**Status:** Accepted  
**Date:** 2026-07-15  
**Context:** [CONTEXT.md](../../CONTEXT.md) · Design detail: [architecture/idp-functional-agents.md](../architecture/idp-functional-agents.md)

## Context

Repody today implements **Intelligent Document Processing (IDP)** only: ingest → extract →
validate → review. Product direction is a **three-agent platform**:

| Agent | Role |
|-------|------|
| **IDP** | Document ingest, extraction, document/business rules |
| **Fraud detection** | Risk / anomaly analysis (later) |
| **Computer use** | UI/system automation (later) |

Without an explicit boundary, Fraud and Computer Use tend to get stuffed into
`extraction/` or `app/run/validation.py`. Run lifecycle DDD
(`app/run/lifecycle.py`, formerly under `domain/`) is already a good platform seam; IDP business logic was not
yet a clean agent slice (mixed orchestration + I/O in phase functions).

## Decision

1. **Platform vs agents** — Shared runtime (run claim/complete, Taskiq, auth, SSE,
   storage) stays platform-owned. IDP / Fraud / Computer Use are **peer agent slices**.
2. **Functional-first IDP** — Prefer small pure functions, frozen data contracts,
   composition, and thin adapters. Avoid deep class hierarchies for the IDP pipeline.
3. **Errors as data** — Use `Result[T]` / `AppError` at pipeline boundaries; allow
   per-document soft failures on `IdpOutcome.errors`.
4. **Handoff type** — `IdpOutcome` wrapped in `AgentOutcome` is the extension point
   for Fraud and Computer Use.
5. **Strangler migration** — Introduce `audit_workbench.runtime.contracts` and
   `audit_workbench.agents.idp` alongside existing modules; switch `process_run`
   only after compose + adapters are tested. No big-bang rewrite.

## Consequences

**Positive**

- Clear home for future Fraud / Computer Use without rewriting IDP again
- Testable pure core (plan, parse, logic eval, summarize)
- Aligns product language (“plateforme d’agents”) with code structure

**Negative / tradeoffs**

- Temporary dual vocabulary during early migration (`AgentOutcome` vs audit DTOs)
- Run entity remains a mutable dataclass for ORM mapping simplicity; transitions are pure functions

## Non-goals

- Rewriting Helm, auth/Casbin, or the frontend in this ADR
- Mandatory always-on IDP → Fraud → Computer Use chain
- Empty plugin frameworks or Agent base-class hierarchies

## Migration phases

1. Contracts + architecture lint — **done**
2. ORM/snapshot → `IdpInput` mappers + tests — **done**
3. Pure extract/validate functions + thin wrappers — **done**
4. Adapters + `compose_idp` + `execute_idp_run` wired from `process_run` — **done**
5. Delete obsolete god-phase logic; recipe stubs for Fraud / Computer Use; replace extractor ABC / use-case classes with callables — **done**

## References

- [Taskiq ADR](./001-taskiq-async-runs.md) — async runs stay platform/queue
- [Clean Architecture skill](../../.agents/skills/clean-architecture/SKILL.md) — dependency rule
- PEP 544 Protocols / callables for ports (not inheritance trees)
- As-built layout: [idp-functional-agents.md](../architecture/idp-functional-agents.md) · Run lifecycle: `app/run/lifecycle.py` · Recipe: `runtime/recipe.py` · Staged queues: [ADR 007](./007-staged-agent-queues-taskiq.md)
