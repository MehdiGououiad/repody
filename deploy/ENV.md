# Environment variables

Single reference for secrets and `AUDIT_*` configuration.

Production and local values are supplied through Helm values and Kubernetes Secrets.
Local kind uses `deploy/helm/repody/values-local.yaml`.

## Production Secret

When `secrets.create=false`, create `repody-runtime-secrets` with:

| Key | Purpose |
|-----|---------|
| `AUTH_SECRET` | Auth.js session encryption |
| `AUTH_KEYCLOAK_CLIENT_SECRET` | Keycloak client secret for `repody-web` |
| `AUDIT_VLLM_API_KEY` | Optional bearer token for external VLM |

## External Inference

| Variable / value | Purpose |
|------------------|---------|
| `AUDIT_INFERENCE_MODE=vllm` | Use external OpenAI-compatible document-model runtime |
| `AUDIT_VLLM_BASE_URL` | Endpoint root, e.g. `https://vlm.example.com/v1` |
| `AUDIT_VLLM_SERVED_MODEL` | Model id from `/v1/models` |
| `AUDIT_VLLM_API_KEY` | Optional bearer token |
| `AUDIT_REPODY_VLM_WARMUP_ON_START=false` | Recommended for remote/serverless endpoints |

Helm values:

```yaml
config:
  inferenceMode: vllm
  vllmBaseUrl: https://vlm.example.com/v1
  vllmServedModel: numind/NuExtract3

workerOcr:
  warmupOnStart: false
```

## Platform Behavior

| Variable | Production value | Description |
|----------|------------------|-------------|
| `AUDIT_SEED_ON_STARTUP` | `false` | Demo data on API boot |
| `AUDIT_USE_CREATE_ALL` | `false` | Use Alembic migrations |
| `AUDIT_RUN_MIGRATIONS_ON_STARTUP` | `true` | Alembic on API start |
| `AUDIT_OIDC_ENABLED` | `true` | JWT auth on management API |
| `AUDIT_OIDC_AUDIENCE` | required | Expected JWT audience |
| `AUDIT_RATE_LIMIT_FAIL_CLOSED` | `true` | Reject when rate limit backend is unavailable |
| `AUDIT_DIRECT_UPLOAD_ENABLED` | `true` | Presigned object-storage uploads |
| `AUDIT_STORAGE_BACKEND` | `s3` | Object storage |
| `AUDIT_LOG_JSON` | `true` | Structured logs |
| `AUDIT_CORS_ORIGINS` | JSON array | Browser origins |

## Image Build

| Variable | Purpose |
|----------|---------|
| `REPODY_IMAGE_REGISTRY` | e.g. `ghcr.io/org` |
| `REPODY_IMAGE_TAG` | Image tag (`latest` default) |
| `REPODY_WEB_BACKEND_URL` | Backend URL baked into web image rewrites |

Used by `pnpm images:build` and `pnpm images:push`.

## Local (kind) overrides

Set before `pnpm k8s:local` to point workers at an external VLM:

| Variable | Description |
|----------|-------------|
| `REPODY_VLLM_BASE_URL` | External OpenAI-compatible root, e.g. `http://host.docker.internal:1234/v1` |
| `REPODY_VLLM_SERVED_MODEL` | Model id from `/v1/models` |

Observability and Bugsink DSNs are configured in Helm values (`observability.bugsinkDsn`) or the runtime Secret (`BUGSINK_DSN`, `NEXT_PUBLIC_BUGSINK_DSN` at web image build).
