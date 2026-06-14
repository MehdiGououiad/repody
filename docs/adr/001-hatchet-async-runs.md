# ADR 001: Hatchet for async audit runs

**Status:** Accepted  
**Date:** 2026-06-13  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Audit runs can take seconds to minutes (PDF render, Repody VLM inference, rule evaluation). The API must accept run requests quickly, survive process restarts, and scale extraction separately from fast logic-only work.

Earlier experiments referenced queue workers generically; the platform now standardizes on **Hatchet** (`hatchet-lite` in Docker, `hatchet-sdk` in Python).

## Decision

Use **Hatchet** as the workflow engine for audit runs:

- Workflow: `audit-run` in `backend/src/audit_workbench/hatchet/workflows/`
- Workers register with pool labels: `ocr` (document-model jobs) and `fast` (logic-only)
- API dispatches via `services/run_dispatch.py`; workers execute `services/run_processor.py`
- `AUDIT_RUN_JOBS_INLINE=true` bypasses Hatchet for solo local dev (`pnpm dev:api`)

## Consequences

**Positive**

- Durable task queue with visible runs in Hatchet UI (`http://localhost:8888`)
- Independent scaling of OCR vs fast worker pools
- Task timeouts map to `AUDIT_HATCHET_TASK_TIMEOUT_MINUTES`

**Negative**

- Extra infrastructure: `hatchet-postgres`, `hatchet-lite`, `hatchet-init` token bootstrap
- Local dev requires either inline mode or running worker containers
- `.env.example` and docs must say **Hatchet**, not legacy queue names

## Alternatives considered

| Option | Why not |
|--------|---------|
| Inline-only (no queue) | Blocks API workers; no horizontal scale |
| ARQ / Redis queue | Less workflow visibility; superseded before production hardening |
| Celery | Heavier ops footprint for current team size |

## References

- `compose.yaml` — Hatchet services
- `backend/src/audit_workbench/hatchet/worker.py`
- [DEPLOY.md](../../DEPLOY.md) — Hatchet env vars
