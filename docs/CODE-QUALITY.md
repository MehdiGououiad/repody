# Code Quality Review

This is the review-facing map for keeping Repody simple, testable, and free of
dead code and needless indirection. It complements [CONTEXT.md](../CONTEXT.md), which is the
domain and architecture glossary, and [DEVELOPMENT.md](./DEVELOPMENT.md), which is the
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
| Framework rules | ESLint, narrowed to Next.js-specific rules and React Hooks | - |
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
  lives in module-level functions that take their state explicitly. A
  swappable dependency is a `typing.Protocol` with one real implementation
  and a test fake - see `Store` in `backend/src/repody/infra/storage.py`.
- **No pass-through re-exports.** Import from the module that defines a symbol.
  A barrel is acceptable only for a types-only module that is erased at compile
  time, such as `lib/types.ts`.
- **Raise `AppError` for application failures.** Use cases raise
  `AppError(status, message, retry_after=...)` (`backend/src/repody/app/errors.py`, plain Python
  so the use cases stay framework-free); one handler in `backend/src/repody/main.py` answers
  it with the status, `detail` and `Retry-After`. Inside `except`, raise `... from exc`.
- **Shared helpers have one home.** Display formatting (durations, bytes,
  percentages) lives in `lib/utils.ts`; dates render through
  `components/shared/date-time.tsx`; clipboard copy in `lib/hooks/use-copy-to-clipboard.ts`.
- **One source per contract.** Status values are Python `Literal`s; the database CHECKs, the
  OpenAPI schema and the generated TypeScript types all come from them. The rule operators each
  field type takes come from `GET /v1/catalog`, not a frontend copy.

## Backend Layers

Dependencies point inward. `pnpm architecture:check` fails the build when they do not.

| Package | May import | Must not import |
|---------|------------|-----------------|
| `api/` (routes, caller dependencies) | everything below | - |
| `app/` (use cases) | `extraction`, `rules`, `schemas`, `models`, `queue`, `storage`, `settings` | `fastapi`, `starlette`, `api` |
| `extraction/`, `rules/` (domain) | `schemas`, `settings` (extraction only) | `app`, `api`; `rules` also no DB, Redis or settings |
- **Suppressions must explain themselves.** Every `biome-ignore`,
  `# noqa` and `# pyright:` comment states why the rule does not apply.

## Architecture Checklist

| Area | Expected shape | Review signal |
|------|----------------|---------------|
| Run state | Conditional UPDATEs, all in `app/lifecycle.py` (`move_runs`, `fail_run`) | A transition that does not match the current status changes nothing |
| Rules | Typed `Condition` models evaluated directly (`rules/evaluate.py`) | No generated expression text, no `dict` rules |
| HTTP layer | `api/` validates auth, request/response shape, and delegates | Routers should not contain business rules |
| Worker layer | `infra/queue.py` / `worker.py` deliver; `app/execute.py` processes | Worker claims the run, processes it, records terminal failure |
| Deployment | `deploy/helm/` and `compose.yaml` express runtime modules | Docs and env examples name the same variables as settings |
| Frontend | `app/` pages stay thin; reusable UI lives in `components/`; API calls live in `lib/api/` | UI code does not duplicate backend contracts by hand when generated types exist |

## Current Strong Modules

- `app/execute.py`: the whole run, from claim to report, in one module.
- `rules/`: models, values, tables and evaluation in four small modules.
- `schemas/workflow.py`: one Pydantic definition for the API, the database and each run.
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
| Backend logic | `pnpm test:api` |
| Run lifecycle or queue behavior | `pnpm test:unit` then `pnpm test:integration` |
| Architecture dependency rules | `pnpm architecture:check` (import-linter contracts in `backend/pyproject.toml`) |
| Frontend code | `pnpm lint` and `pnpm typecheck` |
| Unused files, exports or dependencies | `pnpm deadcode` |
| API contract changes | `pnpm codegen:api` then `pnpm typecheck` |
| Helm, Compose or images | `pnpm deploy:check` |

## Documentation Rules

- `README.md`: product overview and the laptop path.
- `docs/README.md`: “I want to…” hub.
- `docs/LOCAL.md` / `docs/CLUSTER.md`: laptop vs cluster how-tos.
- `docs/COMMANDS.md`: canonical command list (must match `package.json`).
- `CONTEXT.md`: architecture vocabulary and domain glossary.
- `docs/adr/`: accepted decisions that future reviews should not relitigate.

When code changes behavior, update the smallest doc that owns that behavior and add
cross-links rather than duplicating full instructions in multiple files.
