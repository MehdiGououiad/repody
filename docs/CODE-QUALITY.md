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

## House Style And Who Enforces It

One tool owns each concern, so a given problem is reported exactly once and no
rule is a matter of opinion in review.

| Concern | TypeScript / JavaScript | Python |
|---------|-------------------------|--------|
| Formatting | Biome (`biome.json`) | ruff format (`[tool.ruff.format]`) |
| Linting | Biome | ruff (`[tool.ruff.lint]`) |
| Framework rules | ESLint, narrowed to Next.js-specific rules and React Hooks | — |
| Types | `tsc --noEmit` | pyright |
| Dead code | knip | ruff `F401`/`ARG`, plus review |

Shared conventions: 100-column lines, LF endings, two-space indentation in
TS/JS and four in Python, double quotes, sorted imports, absolute imports only
(`ban-relative-imports = "all"` on the backend, `@/` aliases on the frontend).
`.editorconfig` and `.gitattributes` keep editors and Git in agreement.

`eslint.config.mjs` programmatically disables every rule belonging to a plugin
Biome already covers, so the two linters never disagree about the same line.

### Style Rules Worth Knowing

- **Functions and records over classes.** Classes are for data
  (frozen dataclasses, Pydantic models, SQLAlchemy models) or for interfaces a
  third-party framework demands (Starlette middleware, SDK adapters). Behaviour
  lives in module-level functions that take their state explicitly, or in
  closures bundled into a frozen record of callables — see
  `infra/storage/base.py` and `agents/idp/run.py`.
- **No pass-through re-exports.** Import from the module that defines a symbol.
  A barrel is acceptable only for a types-only module that is erased at compile
  time, such as `lib/types/index.ts`.
- **Errors as data at boundaries.** Domain paths return `Result[T]` with an
  `AppError`; `api/errors.py` maps those to HTTP. Raise exceptions only at the
  outer adapters.
- **Suppressions must explain themselves.** Every `biome-ignore`,
  `# noqa` and `# pyright:` comment states why the rule does not apply.

## Architecture Checklist

| Area | Expected shape | Review signal |
|------|----------------|---------------|
| Run lifecycle | `app/run/lifecycle.py` owns status transitions and events | Tests can exercise lifecycle without FastAPI, SQLAlchemy, Redis, or Taskiq |
| Run use cases | `app/run/commands.py` orchestrates lifecycle plus injected ports | Use cases receive load/save/commit/publish callables; SQLAlchemy stays in `persistence.py` |
| Run persistence | `app/run/persistence.py` + `events.py` | Infrastructure mapping; no business transitions |
| IDP agent | `agents/idp/compose.py` pure; I/O in `adapters/` + `run.py` | Do not put DB/HTTP inside `compose_idp` |
| HTTP layer | `api/` validates auth, request/response shape, and delegates | Routers should not contain business rules |
| Worker layer | `taskiq/` and `run/processor.py` are delivery adapters | Worker claims work, runs recipe, records terminal failure |
| Deployment | `deploy/helm/` and `compose.yaml` express runtime modules | Docs and env examples name the same variables as settings |
| Frontend | `app/` pages stay thin; reusable UI lives in `components/`; API calls live in `lib/api/` | UI code does not duplicate backend contracts by hand when generated types exist |

## Current Strong Modules

- `app/run/lifecycle.py`: deep module for audit Run state changes.
- `app/run/persistence.py`: SQLAlchemy gateway that maps ORM rows to `RunEntity` and back.
- `agents/idp/compose.py`: pure extract+validate composition behind injected ports.
- `app/workflow/`: workflow orchestration and persistence are separated.
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

That is `pnpm verify` (lint, format, types and dead code for both languages)
followed by the backend test suite and the deployment checks. CI runs the same
commands, so a green local `verify` predicts a green pipeline.

Reformat everything in place with `pnpm format`; apply the safe lint fixes with
`pnpm lint:fix` and `pnpm lint:py:fix`.

During day-to-day work, run the smallest command that covers the change:

| Change type | Command |
|-------------|---------|
| Anything, before pushing | `pnpm verify` |
| Backend logic | `pnpm test:api` or `pnpm test:platform:report` |
| Run lifecycle or queue behavior | `pnpm test:unit` then `pnpm test:integration` |
| Architecture dependency rules | `pnpm architecture:check` |
| Frontend code | `pnpm lint` and `pnpm typecheck` |
| Unused files, exports or dependencies | `pnpm deadcode` |
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
