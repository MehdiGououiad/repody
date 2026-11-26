# Development

How the code is laid out, how to test it, and where scripts live. Start the stack first:
[LOCAL.md](./LOCAL.md) (`bun run platform dev` for reloading). Commands:
[COMMANDS.md](./COMMANDS.md). Review rules: [CODE-QUALITY.md](./CODE-QUALITY.md).

## Layout

| Path                  | What it is                                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------------------------------- |
| `app/`                | Next.js routes (thin pages)                                                                                 |
| `components/`         | The web app's UI, by area (`audit/`, `workflow/`, `admin/`, …); `ui/` wraps ui-sdk parts                    |
| `lib/`                | Typed API clients (`lib/api/`, generated from the OpenAPI document), hooks, helpers                         |
| `messages/`, `i18n/`  | English and French text (next-intl)                                                                         |
| `backend/src/repody/` | The Python package: API, use cases, extraction, rules, infrastructure                                       |
| `backend/alembic/`    | Database migrations                                                                                         |
| `deploy/`             | The VPS stack, the Modal model app, Keycloak, Helm, observability ([deploy/README.md](../deploy/README.md)) |
| `e2e/`                | Playwright tests and their sample documents                                                                 |
| `site/`               | The marketing site, a separate Next.js project                                                              |
| `benchmarks/ocr/`     | The extraction accuracy benchmark (run by hand)                                                             |

The backend's layers and what each module owns: [CONTEXT.md](../CONTEXT.md#backend-layers).
Import rules between them are checked by import-linter (`bun run architecture:check`).

The hot path: `app/execute.py` `process_run` → `extraction/pipeline.py` `extract` →
`rules/evaluate.py` `evaluate_rules` ([ADR 009](./adr/009-simple-backend.md)).

## The API contract

The backend's Pydantic models are the source of the API. After changing a route or a schema:

```bash
bun run codegen:api
```

It writes `lib/api/openapi.json`, `lib/api/generated/schema.d.ts` and `lib/api/catalog.json`.
CI fails when any of the three differs from the code (OpenAPI drift).

A schema change needs a new Alembic revision (`backend/alembic/versions/`); never edit one that
has shipped.

## Tests

| Where                        | What                                                                         |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `backend/tests/unit/`        | Pure code: rendering, the model request, rules, settings                     |
| `backend/tests/integration/` | The app on Postgres, each run processed inline (no Hatchet), the model faked |
| `backend/tests/live/`        | A running stack (`E2E_API_URL`)                                              |
| `lib/**/*.test.ts`           | Frontend helpers (`bun test`)                                                |
| `e2e/tests/`                 | Playwright, in the browser, against the local stack                          |

The integration tests create and migrate a `repody_test` database on the local Postgres
(`AUDIT_DATABASE_URL` to use another).

Playwright against a Compose stack: set `E2E_API_URL`, `E2E_WEB_URL=http://localhost:3000` and
`E2E_AUTH_URL`, then `bun run test:platform`. The tests sign in as `E2E_KEYCLOAK_USER` /
`E2E_KEYCLOAK_PASSWORD` in the browser, and call the API as the `repody-e2e` service account
(`E2E_KEYCLOAK_CLIENT_ID` / `E2E_KEYCLOAK_CLIENT_SECRET`, with the operator role).

## Scripts

| Where              | What                                                  |
| ------------------ | ----------------------------------------------------- |
| `scripts/`         | Node helpers that `package.json` calls                |
| `deploy/scripts/`  | The local platform CLI, llama-server, deploy checks   |
| `deploy/vps/`      | The VPS's own tools (deploy, backups, smoke test)     |
| `backend/scripts/` | Python tools, run with `uv run --directory backend …` |

## Versions

Runtimes: Python 3.14, Node 26, Bun 1.4.4. Image pins: [`compose.yaml`](../compose.yaml)
(local), [`deploy/vps/compose.yaml`](../deploy/vps/compose.yaml) (the hosted demo) and the Helm
`values.yaml`. Third-party images are pinned by version and digest, Repody's own by an
immutable tag (a commit or a release); nothing uses `latest`.
