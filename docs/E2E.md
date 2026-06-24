# Platform end-to-end tests

Two layers exercise the full stack against a **running** API and web app:

| Layer | Command | What it covers |
|-------|---------|----------------|
| **Live API (full)** | `pnpm test:platform:live` | All `@pytest.mark.live` API + extraction scenarios against running stack |
| API journey | `pnpm test:platform:api` | Health, workflows, dry-run, test-run, audits, deploy, API run + poll |
| UI (Playwright) | `pnpm test:e2e` | Dashboard, workflows, builder test run, audit report, optional document upload |
| **Both** | `pnpm test:platform` | Waits for services, then API + UI |
| **CI smoke** | `pnpm test:e2e:smoke` | PR CI (`k8s-smoke` job) + manual |

In-process API tests (`pnpm test:api`) use **Postgres + Alembic** in CI (GitHub service container). Default test DB: `postgresql+asyncpg://audit:audit@localhost:5432/audit_workbench_test`.

## Prerequisites

1. **Local Kubernetes stack** running:

```powershell
pnpm k8s:local:hosts    # once (admin)
pnpm k8s:local
pnpm k8s:local:smoke    # optional sanity check
```

2. **Playwright browser** (once per machine):

```powershell
pnpm exec playwright install chromium
```

## Run everything

```powershell
$env:E2E_API_URL = "http://api.repody.local"
$env:E2E_WEB_URL = "http://app.repody.local"
$env:E2E_AUTH_URL = "http://auth.repody.local"
pnpm test:platform
```

When OIDC is enabled, Playwright global setup signs in as `operator@repody.local` and live pytest clients fetch a Keycloak bearer token automatically (override with `E2E_KEYCLOAK_USER` / `E2E_KEYCLOAK_PASSWORD`). Artifacts are saved under `e2e/.auth/`. K8s local does not seed on boot — global setup seeds demo workflow data when `wf-invoice-audit` is missing.

**Operator RBAC (OIDC on):** live API tests expect `403` for operator-only calls to `/v1/metrics` and `/v1/platform/config` (admin-only). Workflow API-key auth checks use an unauthenticated HTTP client so the default JWT is not sent.

**Document extraction (live):** tests that upload `Facture.pdf` and call the VLM are skipped when `GET /v1/healthz` reports `modelRunner != true`. Point k8s local at vLLM or llama-server (see `deploy/llamacpp/` and `docs/REPODY-VLM.md`) to run the full extraction suite.

## UI only / API only

```powershell
pnpm test:e2e
pnpm test:e2e:smoke
pnpm test:e2e:ui
pnpm test:platform:api
pnpm test:platform:live
pnpm test:platform:integration
```

### CI (GitHub Actions)

The `k8s-smoke` job in `.github/workflows/ci.yml` runs on every push/PR:

1. `pnpm k8s:local` (kind + Helm)
2. `pnpm test:e2e:smoke`
3. Live pytest against `http://api.repody.local`

## Sample document

1. Drop `sample-invoice.pdf` (or `.png` / `.jpg`) into `e2e/fixtures/documents/`
2. Re-run `pnpm test:e2e` — the **document upload** spec runs automatically

Or point to any file:

```powershell
$env:E2E_SAMPLE_DOCUMENT = "C:\path\to\invoice.pdf"
pnpm test:e2e
```

Until a document is present, upload tests are **skipped** (other specs still run).

## Reports

- Playwright HTML: `e2e/report/index.html`
- Traces/screenshots on failure under `test-results/`
