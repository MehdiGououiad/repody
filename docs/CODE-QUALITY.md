# Code Quality Review

This is the review-facing map for keeping Repody simple, testable, and free of
generated-code smells. It complements [CONTEXT.md](../CONTEXT.md), which is the
domain and architecture glossary, and [BACKEND.md](./BACKEND.md), which is the
backend source inventory.

## Review Goals

- Keep business rules behind small, named modules with clear interfaces.
- Keep framework, database, queue, and HTTP details at the outer adapters.
- Keep docs in sync with commands and deployed shape.
- Prefer deletion of shallow modules over adding new pass-through layers.
- Verify changes with the narrowest useful automated checks before merging.

## Architecture Checklist

| Area | Expected shape | Review signal |
|------|----------------|---------------|
| Run lifecycle | `services/run/domain/` owns status transitions and events | Tests can exercise lifecycle without FastAPI, SQLAlchemy, Redis, or Taskiq |
| Run use cases | `services/run/application/` orchestrates domain plus ports | Use cases receive lifecycle store ports; SQLAlchemy sessions stay in adapters |
| Run adapters | `services/run/adapters/` maps domain to SQLAlchemy and progress/SSE side effects | Adapter code imports infrastructure; domain code does not |
| HTTP layer | `api/` validates auth, request/response shape, and delegates | Routers should not contain business rules |
| Worker layer | `taskiq/` and `run_processor.py` are delivery adapters | Worker code claims work, calls phases, and records terminal failure |
| Deployment | `deploy/helm/` and `compose.yaml` express runtime modules | Docs and env examples name the same variables as settings |
| Frontend | `app/` pages stay thin; reusable UI lives in `components/`; API calls live in `lib/api/` | UI code does not duplicate backend contracts by hand when generated types exist |

## Current Strong Modules

- `services/run/domain/lifecycle.py`: deep module for audit Run state changes.
- `services/run/adapters/persistence.py`: SQLAlchemy gateway that maps ORM rows to `RunEntity` and back.
- `services/workflow/`: workflow orchestration and persistence are separated.
- `catalog/`: model catalog and live probes are centralized instead of scattered across routers.
- `docs/COMMANDS.md`: single command reference for development, release, and client checks.

## Smells To Reject In Review

- Business rules directly inside FastAPI routers, React pages, Taskiq task bodies, SQLAlchemy models, or Helm templates.
- New modules whose interface is almost the same size as the implementation.
- One-adapter seams unless a second adapter is planned and documented.
- Environment variables documented in only one place but consumed elsewhere with a different default.
- Test-only exports or fake abstractions that make production code harder to read.
- Workspace log files for platform logs. Use `kubectl`, Grafana, or terminal output.

## Verification Commands

Before an external review, run the full gate:

```powershell
pnpm review:check
```

During day-to-day work, run the smallest command that covers the change:

| Change type | Command |
|-------------|---------|
| Backend logic | `pnpm test:api` |
| Run lifecycle or queue behavior | `node scripts/backend-run.mjs --dev pytest tests/test_services -q` |
| Architecture dependency rules | `pnpm architecture:check` |
| Frontend code | `pnpm lint` and `pnpm typecheck` |
| API contract changes | `pnpm codegen:api` then `pnpm typecheck` |
| Helm or client packaging | `pnpm helm:lint`, `pnpm helm:template`, `pnpm client:check` |
| Production readiness | `pnpm prod:readiness` |

## Documentation Rules

- `README.md`: product overview and fastest correct start.
- `DEV.md`: daily developer workflow.
- `DEPLOY.md`: short deployment entry point.
- `docs/README.md`: full docs map.
- `docs/COMMANDS.md`: canonical command list.
- `CONTEXT.md`: architecture vocabulary, domain glossary, and context decisions.
- `docs/adr/`: accepted decisions that future reviews should not relitigate.

When code changes behavior, update the smallest doc that owns that behavior and add
cross-links rather than duplicating full instructions in multiple files.
