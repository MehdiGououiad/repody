# ADR 001: Hatchet for async audit runs

**Status:** Accepted  
**Date:** 2026-06-13  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Audit runs can take seconds to minutes (PDF render, Repody VLM inference, rule evaluation). The API must accept run requests quickly, survive process restarts, and scale extraction separately from fast logic-only work.

The platform standardizes on **Hatchet** (`hatchet-stack` locally via Helm subchart, external Hatchet in production; `hatchet-sdk` in Python).

## Decision

Use **Hatchet** as the workflow engine for audit runs:

- Workflow: `audit-run` in `backend/src/audit_workbench/hatchet/workflows/`
- Workers register with pool labels: `ocr` (document-model jobs) and `fast` (logic-only)
- API dispatches via `services/run_dispatch.py`; workers execute `services/run_processor.py`
- Local dev and CI run Hatchet workers in the kind cluster (`pnpm k8s:local` / `pnpm dev`) using the official [`hatchet-stack`](https://docs.hatchet.run/self-hosting/kubernetes-quickstart) Helm chart (engine + API + Postgres + RabbitMQ).

## Consequences

**Positive**

- Durable task queue; Hatchet UI via `kubectl port-forward` to `repody-hatchet-frontend` (not exposed on Gateway API)
- Independent scaling of OCR vs fast worker pools
- Task timeouts map to `AUDIT_HATCHET_TASK_TIMEOUT_MINUTES`

**Negative**

- Extra infrastructure: Hatchet Postgres + RabbitMQ + engine/API (local `hatchet-stack` subchart)
- Local dev requires a running Kubernetes stack with worker Deployments

## Alternatives considered

| Option | Why not |
|--------|---------|
| Inline-only (no queue) | Blocks API workers; no horizontal scale |
| ARQ / Redis queue | Less workflow visibility |
| Celery | Heavier ops footprint for current team size |

## References

- `deploy/helm/repody/templates/workers.yaml` — worker Deployments
- `backend/src/audit_workbench/hatchet/worker.py`
- [DEPLOY.md](../../DEPLOY.md) — Hatchet env vars
