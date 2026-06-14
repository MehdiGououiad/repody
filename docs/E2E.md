# Platform end-to-end tests

Two layers exercise the full stack against a **running** API and web app:

| Layer | Command | What it covers |
|-------|---------|----------------|
| API journey | `pnpm test:platform:api` | Health, workflows, dry-run, test-run, audits, deploy, API run + poll |
| UI (Playwright) | `pnpm test:e2e` | Dashboard, workflows, builder test run, audit report, optional document upload |
| **Both** | `pnpm test:platform` | Waits for services, then API + UI |
| **CI smoke** | `pnpm test:e2e:smoke` | Nightly + manual in GitHub Actions (not on every push) |

In-memory API tests (no stack required): `pnpm test:api`.

## Prerequisites

1. **Postgres + API** (pick one):
   - `docker compose up -d postgres api`
   - Or local: `pnpm dev:api` with `AUDIT_DATABASE_URL` set
2. **Web**: `pnpm dev` (port 3000)  
   Or full stack: `docker compose up` (ensure web image was built with `BACKEND_URL=http://api:8000`).

3. **Playwright browser** (once per machine):

```powershell
pnpm exec playwright install chromium
```

## Run everything

```powershell
pnpm test:platform
```

Environment overrides:

```powershell
$env:E2E_API_URL = "http://localhost:8000"
$env:E2E_WEB_URL = "http://localhost:3000"
pnpm test:platform
```

## UI only / API only

```powershell
pnpm test:e2e
pnpm test:e2e:smoke        # same subset as nightly CI workflow
pnpm test:e2e:ui          # interactive UI
pnpm test:platform:api    # live API journey only
```

### CI stack (GitHub Actions)

Runs **nightly** and on **workflow_dispatch** only (Actions → E2E smoke → Run workflow). Not triggered on every push — use `pnpm test:e2e:smoke` locally before merge if needed.

```powershell
docker compose -f compose.yaml -f compose.e2e.yaml up -d --build --wait
pnpm test:e2e:smoke
```

## Sample document (your file)

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

## CI sketch

```yaml
- run: docker compose up -d --wait
- run: pnpm exec playwright install chromium --with-deps
- run: pnpm test:platform
  env:
    E2E_API_URL: http://localhost:8000
    E2E_WEB_URL: http://localhost:3000
```
