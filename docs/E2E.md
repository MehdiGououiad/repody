# Platform end-to-end tests

Command reference: [COMMANDS.md](./COMMANDS.md).

## Layers

| Layer | Command | Needs cluster |
|-------|---------|---------------|
| Unit / integration | `pnpm test:api` | No |
| Playwright smoke | `pnpm test:e2e:smoke` | Optional (deployed cluster) |
| Full platform | `pnpm test:platform` | Optional (deployed cluster) |
| UI only | `pnpm test:e2e` | Optional |

## Compose dev (default)

With `pnpm dev:all` running:

```powershell
$env:E2E_API_URL = "http://127.0.0.1:8000"
$env:E2E_WEB_URL = "http://localhost:3000"
$env:E2E_AUTH_URL = "http://127.0.0.1:8080"
pnpm test:platform
```

Use **`localhost`** for the web URL (NextAuth cookies). API and Keycloak can use `127.0.0.1`.

API-only tests: `pnpm test:api` (no cluster).

## Against a deployed cluster

Point E2E at the client's Ingress hosts (replace with real URLs):

```powershell
$env:E2E_WEB_URL="https://app.example.com"
$env:E2E_API_URL="https://api.example.com"
$env:E2E_AUTH_URL="https://auth.example.com"
$env:E2E_K8S_NAMESPACE="repody"
pnpm test:platform
```

Cluster install: [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md).

**Document extraction (live):** skipped when `GET /v1/healthz` reports `llamacpp != true` (when probing is enabled). Configure external inference — [REPODY-VLM.md](./REPODY-VLM.md).
## Sample document

See [e2e/fixtures/documents/README.md](../e2e/fixtures/documents/README.md).
