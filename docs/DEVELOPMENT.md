# Development

Backend layout, tests, and script ownership. Laptop start: [LOCAL.md](./LOCAL.md). Commands: [COMMANDS.md](./COMMANDS.md). Architecture: [CONTEXT.md](../CONTEXT.md).

## Backend

**Package:** `repody` (`backend/src/repody/`) · FastAPI on `/v1/*`.

| Area | Role |
|------|------|
| `api/` | Thin HTTP routers |
| `app/` | Use cases (run, workflow, operator, uploads, …) |
| `agents/idp/` | IDP extract + validate ([ADR 006](./adr/006-three-agent-functional-idp.md)) |
| `runtime/` | Contracts, recipe, pools, run status |
| `catalog/` | Document-model registry + probes |
| `extraction/` | Pipeline + model adapters |
| `inference/` | OpenAI-compat clients |
| `rules/` | Logic + LLM evaluators |
| `taskiq/` | Worker broker + tasks |
| `infra/` | DB, auth, storage, observability |
| `schemas/`, `settings/` | DTOs · `AUDIT_*` settings |

Hot path: `process_run` → `execute_platform_run` → `compose_idp` → `complete_run`.

Python ops scripts: [backend/scripts/README.md](../backend/scripts/README.md).

## Testing

```text
backend/tests/unit|integration|live/
e2e/tests/                 # Playwright
reports/platform-tests/    # pnpm test:platform:report
```

| Command | What |
|---------|------|
| `pnpm test:unit` / `test:integration` | Fast layers |
| `pnpm test:api` | Unit + integration (CI default) |
| `pnpm test:live` | Needs running stack |
| `pnpm test:e2e:smoke` | Playwright smoke |
| `pnpm test:platform:report` | Report under `reports/platform-tests/` |
| `pnpm review:check` | Full gate — [CODE-QUALITY.md](./CODE-QUALITY.md) |

Compose E2E: set `E2E_API_URL` / `E2E_WEB_URL=http://localhost:3000` / `E2E_AUTH_URL`, then `pnpm test:platform`. Use **localhost** for the web URL (OIDC cookies).

## Scripts map

| Location | Owns |
|----------|------|
| `scripts/` | Cross-cutting Node from `package.json` |
| `deploy/scripts/` | Platform, model serve, images, release |
| `backend/scripts/` | Python ops via `node scripts/backend-run.mjs` |

## Pinned versions

Canonical images: [`deploy/pinned-images.env`](../deploy/pinned-images.env). Runtimes: Python 3.13 · Node 24 · pnpm 11.7.0. Production never uses `latest`.
