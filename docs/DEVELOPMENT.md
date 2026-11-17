# Development

Backend layout, tests, and script ownership. Laptop start: [LOCAL.md](./LOCAL.md). Commands: [COMMANDS.md](./COMMANDS.md). Architecture: [CONTEXT.md](../CONTEXT.md).

## Backend

**Package:** `repody` (`backend/src/repody/`) · FastAPI on `/v1/*`.

```
backend/src/repody/
├── main.py            FastAPI app, lifespan, error handler
├── api/               HTTP routes (workflows, runs, platform) and caller dependencies
├── app/               Use cases: workflows, runs, execute (worker), progress, maintenance
├── extraction/        NuExtract request, page rendering, llama-server client, field values
├── rules/             Typed conditions and their evaluation
├── schemas/           Pydantic models (API and stored workflow definition)
├── auth.py            Keycloak JWT, roles, workflow API keys
├── queue.py · worker.py   Hatchet client (dispatch, cancel); the worker and its workflows
├── models.py · db.py  SQLAlchemy tables and sessions
├── storage.py         S3 documents
└── settings.py        AUDIT_* settings
```

Hot path: `app/execute.py` `process_run` -> `extraction.pipeline.extract` -> `rules.evaluate.evaluate_rules` ([ADR 009](./adr/009-simple-backend.md)).

Python ops scripts: [backend/scripts/README.md](../backend/scripts/README.md).

## Testing

```text
backend/tests/unit|integration|live/
e2e/tests/                 # Playwright (defaults to the local stack on localhost)
```

| Command | What |
|---------|------|
| `pnpm test:unit` / `test:integration` | Fast layers |
| `pnpm test:api` | Unit + integration (CI default) |
| `pnpm test:live` | Needs running stack |
| `pnpm test:e2e:smoke` | Playwright smoke: sign-in and navigation |
| `pnpm test:e2e` | All Playwright specs against `pnpm platform` |
| `pnpm review:check` | Full gate - [CODE-QUALITY.md](./CODE-QUALITY.md) |

Compose E2E: set `E2E_API_URL` / `E2E_WEB_URL=http://localhost:3000` / `E2E_AUTH_URL`, then `pnpm test:platform`. Use **localhost** for the web URL (OIDC cookies). Tests sign in as `E2E_KEYCLOAK_USER` / `E2E_KEYCLOAK_PASSWORD` in the browser and call the API with the `repody-e2e` service account (client credentials: `E2E_KEYCLOAK_CLIENT_ID` / `E2E_KEYCLOAK_CLIENT_SECRET`); a cluster realm needs that client with the operator role.

## Scripts map

| Location | Owns |
|----------|------|
| `scripts/` | Cross-cutting Node from `package.json` |
| `deploy/scripts/` | Platform, model serve, images, release |
| `backend/scripts/` | Python ops via `uv run --directory backend …` |

## Pinned versions

Local image pins live in [`compose.yaml`](../compose.yaml); Kubernetes pins in the Helm `values.yaml` files. Runtimes: Python 3.14 · Node 26 (LTS) · pnpm 12.16.1. Production never uses `latest`.
