# Development

Backend layout, tests, and script ownership. Laptop start: [LOCAL.md](./LOCAL.md). Commands: [COMMANDS.md](./COMMANDS.md). Architecture: [CONTEXT.md](../CONTEXT.md).

## Backend

**Package:** `repody` (`backend/src/repody/`) · FastAPI on `/v1/*`.

| Area | Role |
|------|------|
| `api/` | Thin HTTP routers |
| `app/` | Use cases (run, workflow, uploads, …) |
| `runtime/` | AppError, run status, metrics |
| `catalog/` | Document model + llama-server status |
| `extraction/` | Pipeline + NuExtract adapter |
| `inference/` | OpenAI-compat clients |
| `rules/` | Logic rule evaluator |
| `taskiq/` | Worker broker + tasks |
| `infra/` | DB, auth, storage, observability |
| `schemas/`, `settings/` | DTOs · `AUDIT_*` settings |

Hot path: `app/run/worker.py` `process_run` -> `extract_document` -> `validate_field_rows` -> `complete_run` ([ADR 008](./adr/008-flat-run-pipeline.md)).

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
| `pnpm review:check` | Full gate - [CODE-QUALITY.md](./CODE-QUALITY.md) |

Compose E2E: set `E2E_API_URL` / `E2E_WEB_URL=http://localhost:3000` / `E2E_AUTH_URL`, then `pnpm test:platform`. Use **localhost** for the web URL (OIDC cookies).

## Scripts map

| Location | Owns |
|----------|------|
| `scripts/` | Cross-cutting Node from `package.json` |
| `deploy/scripts/` | Platform, model serve, images, release |
| `backend/scripts/` | Python ops via `uv run --directory backend …` |

## Pinned versions

Local image pins live in [`compose.yaml`](../compose.yaml); Kubernetes pins in the Helm `values.yaml` files. Runtimes: Python 3.13 · Node 24 · pnpm 12.5.1. Production never uses `latest`.
