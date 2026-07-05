# Platform end-to-end tests

Command reference: [COMMANDS.md](./COMMANDS.md).

## Layers

| Layer | Command | Needs cluster |
|-------|---------|---------------|
| Unit / integration | `pnpm test:api` | No |
| Playwright smoke | `pnpm test:e2e:smoke` | Optional (OpenShift CRC) |
| Full platform | `pnpm test:platform` | Optional (OpenShift CRC) |
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

## OpenShift CRC

After `pnpm openshift:client-test`:

```powershell
$env:E2E_WEB_URL="https://repody-web.apps-crc.testing"
$env:E2E_API_URL="https://repody-api.apps-crc.testing"
$env:E2E_AUTH_URL="https://repody-auth.apps-crc.testing"
$env:E2E_K8S_NAMESPACE="repody"
$env:NODE_TLS_REJECT_UNAUTHORIZED="0"
$env:E2E_IGNORE_TLS="1"
pnpm test:platform
```

See [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md).

**Document extraction (live):** skipped when `GET /v1/healthz` reports `modelRunner != true`. Start host inference — [REPODY-VLM.md](./REPODY-VLM.md).

## Sample document

See [e2e/fixtures/documents/README.md](../e2e/fixtures/documents/README.md).
