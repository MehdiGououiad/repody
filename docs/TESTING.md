# Testing

Repody follows the **test pyramid** (2026 pytest / Playwright practice): many fast unit tests, fewer DB/ASGI integration tests, a thin live/E2E layer, and a single report at the end.

## Layout

```text
backend/tests/
  conftest.py              # shared fixtures (Postgres, ASGI client, live_client)
  helpers/ fixtures/
  unit/                    # pure — no live stack; prefer no DB
    agents/ app/ extraction/ inference/ infra/{auth,observability}/
    runtime/ rules/ taskiq/
  integration/             # ASGI + Postgres (or storage boundary); no workers
    api/ app/ infra/{auth,storage}/
  live/                    # requires running API (+ workers for run completion)
    api/ runtime/ journeys/

e2e/tests/                 # Playwright UI journeys (real browser)
reports/platform-tests/    # generated REPORT.md + HTML + JUnit
```

Markers (also auto-applied from path): `unit`, `integration`, `live`, `e2e`, `slow`, `e2e_facture`.

## Commands

| Command | What runs |
|---------|-----------|
| `pnpm test:unit` | `backend/tests/unit` (`not live and not slow`) |
| `pnpm test:integration` | `backend/tests/integration` (`not live and not slow`) |
| `pnpm test:api` | unit + integration (CI default; excludes live) |
| `pnpm test:live` | `backend/tests/live` (`-m live`) — needs stack |
| `pnpm test:e2e` | Playwright UI |
| `pnpm test:e2e:smoke` | Platform smoke only |
| `pnpm test:platform:report` | Unit + integration + **REPORT.md / index.html** |
| `pnpm test:platform:report:full` | Above + live API + Playwright (stack required) |

## Report

```powershell
pnpm test:platform:report
```

Writes:

- `reports/platform-tests/REPORT.md` — summary table
- `reports/platform-tests/index.html` — same summary in HTML
- `reports/platform-tests/pytest-*.html` — per-layer pytest-html
- `reports/platform-tests/junit-*.xml` — CI JUnit

Full stack report (API live + UI):

```powershell
# stack already up via pnpm dev:all / E2E_STACK=1
pnpm test:platform:report:full
```

## Practices we follow

1. **Strict markers** (`--strict-markers`) — typos fail collection.
2. **Pyramid paths** — layer is visible in the folder name.
3. **Live gated** — `@pytest.mark.live` / `tests/live/` needs `E2E_STACK=1` or `E2E_API_URL`.
4. **HTTP only in API tests** — service boundaries return `Result` / domain errors; assert **mapped** status codes (`VALIDATION→422`, `FORBIDDEN→403`) via `tests/helpers/api_errors.py`.
5. **IDP core** — `compose_idp` covered with injected ports (`unit/agents/test_compose_idp.py`).
6. **Agent peers** — Fraud / Computer Use have contract + SKIPPED-shell unit tests; staging covered by recipe unit + `process_run` staged integration.
7. **Hot path seams** — claim / handoff / finalize have Postgres integration tests (no workers required).
8. **Playwright** — critical journeys only; traces on retry; HTML under `e2e/report/`.

## What each layer should cover

| Platform area | Unit | Integration | Live / UI |
|---------------|------|-------------|-----------|
| Auth / Casbin / IAM | ✓ | ✓ | Playwright auth |
| Run lifecycle / Result | ✓ | ✓ claim / finalize | live run completion |
| Staged agents (recipe) | ✓ flags + shells | ✓ IDP→fraud handoff + finalize | gated multi-agent (optional) |
| IDP compose / validate | ✓ ports | processor | live journey |
| Fraud / Computer Use | ✓ contracts + SKIPPED | via staged processor | when workers ready |
| Rules engine | ✓ | — | cross-doc UI |
| Extraction / catalog | ✓ | — | live / slow |
| Uploads / storage | intent helpers | ✓ status matrix (422/403/404/201) | upload UI |
| Operator | ✓ job store | API | operator console |
| Taskiq / outbox | settings + input | ✓ outbox retry / handoff | live drain |
