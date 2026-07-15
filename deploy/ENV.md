# Environment variables

Single reference for secrets and `AUDIT_*` configuration.

Daily local values are copied from `deploy/env/compose.env.example` into
`backend/.env`, with Auth.js values in `.env.local` from `deploy/env.auth.example`.
Kubernetes values are supplied through Helm values and Kubernetes Secrets (see [docs/deploy/SECRETS.md](../docs/deploy/SECRETS.md)).

## Production Secret

When `secrets.create=false`, create `repody-runtime-secrets` with:

| Key | Purpose |
|-----|---------|
| `AUTH_SECRET` | Auth.js session encryption |
| `AUTH_KEYCLOAK_CLIENT_SECRET` | Keycloak client secret for `repody-web` |
| `AUDIT_LLAMACPP_API_KEY` | Optional bearer token for external VLM |

## External Inference

| Variable / value | Purpose |
|------------------|---------|
| `AUDIT_INFERENCE_MODE=llamacpp` | Use external OpenAI-compatible document-model runtime |
| `AUDIT_LLAMACPP_BASE_URL` | Endpoint root, e.g. `https://vlm.example.com/v1` |
| `AUDIT_LLAMACPP_SERVED_MODEL` | Model id from `/v1/models` |
| `AUDIT_LLAMACPP_API_KEY` | Optional bearer token |
| `AUDIT_REPODY_VLM_WARMUP_ON_START=false` | Recommended for remote/serverless endpoints |

Helm values:

```yaml
config:
  inferenceMode: llamacpp
  llamacppBaseUrl: https://vlm.example.com/v1
  llamacppServedModel: numind/NuExtract3

workerExtract:
  warmupOnStart: false
```

## Platform Behavior

| Variable | Production value | Description |
|----------|------------------|-------------|
| `AUDIT_SEED_ON_STARTUP` | `false` | Demo data on API boot |
| `AUDIT_RUN_MIGRATIONS_ON_STARTUP` | `true` | Alembic on API start |
| `AUDIT_OIDC_ENABLED` | `true` | JWT auth on management API |
| `AUDIT_OIDC_AUDIENCE` | required | Expected JWT audience |
| `AUDIT_RATE_LIMIT_FAIL_CLOSED` | `true` | Reject when rate limit backend is unavailable |
| `AUDIT_RATE_LIMIT_ENABLED` | `true` | Enable run enqueue rate limits |
| `AUDIT_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window |
| `AUDIT_RATE_LIMIT_RUNS_PER_WORKFLOW` | `30` | Max runs per workflow per window |
| `AUDIT_RATE_LIMIT_RUNS_PER_CLIENT` | `120` | Max runs per client per window |
| `AUDIT_DIRECT_UPLOAD_ENABLED` | `true` | Presigned object-storage uploads |
| `AUDIT_STORAGE_BACKEND` | `s3` | Object storage |
| `AUDIT_LOG_JSON` | `true` | Structured logs |
| `AUDIT_CORS_ORIGINS` | JSON array | Browser origins |

## Admission Control

| Variable | Local Compose | Production default | Description |
|----------|---------------|--------------------|-------------|
| `AUDIT_ADMISSION_CONTROL_ENABLED` | default from settings | `true` | Enable queue/inflight admission limits |
| `AUDIT_ADMISSION_MAX_QUEUED` | `50` | `50` | Maximum queued runs before rejecting new work |
| `AUDIT_ADMISSION_MAX_INFLIGHT` | `32` | `64` | Maximum inflight runs across pools |
| `AUDIT_ADMISSION_MAX_EXTRACT_INFLIGHT` | `2` | `8` | Maximum document-model extraction work in flight |
| `AUDIT_ADMISSION_RETRY_AFTER_SECONDS` | `60` | `60` | Retry hint returned when admission rejects work |

## Image Build

| Variable | Purpose |
|----------|---------|
| `REPODY_IMAGE_REGISTRY` | e.g. `ghcr.io/org`; required for `pnpm images:release` and `pnpm images:push` |
| `REPODY_IMAGE_TAG` | Image tag (`latest` default) |
| `REPODY_BACKEND_IMAGE_TAG` | Backend image tag override |
| `REPODY_WEB_IMAGE_TAG` | Web image tag override |
| `REPODY_WEB_BACKEND_URL` | Backend URL baked into web image rewrites |
| `REPODY_BACKEND_EXTRAS` | Backend Python extras (`otel` default) |
| `REPODY_INCLUDE_BENCHMARK_FIXTURES` | Set `true` only when the backend image should include the built-in Facture benchmark fixture |
| `REPODY_BUILDKIT_BACKEND_CACHE_FROM` / `REPODY_BUILDKIT_BACKEND_CACHE_TO` | Backend BuildKit cache refs |
| `REPODY_BUILDKIT_WEB_CACHE_FROM` / `REPODY_BUILDKIT_WEB_CACHE_TO` | Web BuildKit cache refs |

Used by `pnpm images:build`, `pnpm images:push`, and `pnpm images:release`.

## Local Compose

`pnpm dev:setup` copies `deploy/env/compose.env.example` to `backend/.env`.

Use these runtime overrides for local API/UI work:

| Variable | Description |
|----------|-------------|
| `REPODY_API_PORT` | Host API port for `pnpm dev:api` / `pnpm dev:app` (`8000` default) |
| `REPODY_DEV_API_RELOAD` | Set `1` to opt into Uvicorn reload on Windows |
| `AUDIT_LLAMACPP_BASE_URL` | External OpenAI-compatible root, e.g. `http://127.0.0.1:8081/v1` |
| `AUDIT_LLAMACPP_SERVED_MODEL` | Model id from `/v1/models` |

## Kubernetes Lab Overrides

Use Helm values for Kubernetes lab/local overrides:

| Helm value | Env emitted |
|------------|-------------|
| `config.llamacppBaseUrl` | `AUDIT_LLAMACPP_BASE_URL` |
| `config.llamacppServedModel` | `AUDIT_LLAMACPP_SERVED_MODEL` |
| `workerExtract.warmupOnStart` | `AUDIT_REPODY_VLM_WARMUP_ON_START` |

Observability and Bugsink DSNs are configured in Helm values (`observability.bugsinkDsn`) or the runtime Secret (`BUGSINK_DSN`, `NEXT_PUBLIC_BUGSINK_DSN` at web image build).
