# Environment variables

Single reference for secrets and `AUDIT_*` configuration.

Daily local values are copied from `deploy/env/compose.env.example` into
`backend/.env`, with Auth.js values in `.env.local` from `deploy/env.auth.example`.
On Kubernetes, the Helm chart's `config` map is rendered into the ConfigMap as-is (keys are the `AUDIT_*` names below) and credentials come from the `repody-runtime-secrets` Secret ([docs/CLUSTER.md](../docs/CLUSTER.md#2-runtime-secret)).

## Production Secret

`repody-runtime-secrets` holds every credential; the full key list is in
[docs/CLUSTER.md](../docs/CLUSTER.md#2-runtime-secret).

## External Inference

| Variable / value | Purpose |
|------------------|---------|
| `AUDIT_LLAMACPP_BASE_URL` | Endpoint root, e.g. `https://vlm.example.com/v1` |
| `AUDIT_LLAMACPP_SERVED_MODEL` | Model id from `/v1/models` |
| `AUDIT_LLAMACPP_API_KEY` | Optional bearer token |
| `AUDIT_REPODY_VLM_WARMUP_ON_START=false` | Recommended for remote/serverless endpoints |

## Extraction tuning

| Variable | Purpose |
|----------|---------|
| `AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT` | Dual structured+markdown pass; default `false` (markdown-only still works per document) |
| `AUDIT_EXTRACTION_CACHE_ENABLED` | Redis extraction cache; default `false` |

Model HTTP timeouts must stay ≤ `AUDIT_WORKER_TASK_TIMEOUT_MINUTES * 60` (ceiling 15 min).
Compose extract defaults: worker **10** min, model timeouts **600** s, stale **12** min.


Helm values:

```yaml
config:
  AUDIT_LLAMACPP_BASE_URL: https://vlm.example.com/v1
  AUDIT_LLAMACPP_SERVED_MODEL: nuextract3-q4_k_m
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
| `AUDIT_RATE_LIMIT_RUNS_PER_WORKFLOW` | `300` | Max **run creates** per workflow per window |
| `AUDIT_RATE_LIMIT_RUNS_PER_CLIENT` | `2000` | Max **run creates** per client per window |
| `AUDIT_RATE_LIMIT_HTTP_PER_MINUTE` | `6000` | Global per-IP limit for **mutating** methods only (GET browse/poll excluded) |
| `AUDIT_ADMISSION_MAX_QUEUED` | `200` | Reject enqueue (503) when queued ≥ this (`0` disables) |
| `AUDIT_ADMISSION_MAX_INFLIGHT` | `100` | Reject when queued+running ≥ this (`0` disables) |
| `AUDIT_ADMISSION_MAX_EXTRACT_INFLIGHT` | `20` | Reject extract-pool enqueue when extract inflight ≥ this |
| `AUDIT_ADMISSION_RETRY_AFTER_SECONDS` | `15` | `Retry-After` on CAPACITY responses |
| `AUDIT_DB_POOL_SIZE` | `20` | SQLAlchemy pool size per process |
| `AUDIT_DB_MAX_OVERFLOW` | `20` | Extra DB connections beyond pool size |
| `AUDIT_REDIS_MAX_CONNECTIONS` | `64` | Shared Redis pool (cache + SSE) |
| `AUDIT_QUEUE_REFRESH_SSE_LIMIT` | `32` | Max SSE publishes on maintenance queue refresh (`0` = DB-only) |
| `AUDIT_QUEUE_REFRESH_DB_LIMIT` | `128` | Max queued rows loaded/updated per maintenance tick |
| `AUDIT_DIRECT_UPLOAD_ENABLED` | `true` | Presigned object-storage uploads |
| `AUDIT_LOG_JSON` | `true` | Structured logs |
| `AUDIT_CORS_ORIGINS` | JSON array | Browser origins |

## Image Build

Images are defined in [`docker-bake.hcl`](../docker-bake.hcl) (Docker Buildx Bake). Each variable below is read from the environment of the same name; `docker buildx bake -f docker-bake.hcl --print` shows the resolved config.

| Variable | Purpose |
|----------|---------|
| `REPODY_IMAGE_REGISTRY` | e.g. `ghcr.io/org`; required for `pnpm images:release` |
| `REPODY_IMAGE_TAG` | Image tag (`dev` default; `latest` is rejected) |
| `REPODY_BACKEND_IMAGE_TAG` | Backend image tag override |
| `REPODY_WEB_IMAGE_TAG` | Web image tag override |
| `REPODY_IMAGE_PLATFORMS` | e.g. `linux/amd64,linux/arm64` (push only; empty = host platform) |
| `NEXT_PUBLIC_BUGSINK_DSN` | Browser Bugsink DSN inlined into the web bundle |
| `INTERNAL_API_URL` | Runtime web -> API origin (Compose: `http://api:8000`, K8s: `http://repody-api:8000`) |
| `BACKEND_URL` | Fallback origin if `INTERNAL_API_URL` unset |
| `AUTH_KEYCLOAK_INTERNAL_ISSUER` | In-cluster Keycloak issuer for Auth.js server calls (Compose: `http://keycloak:8080/realms/repody`) |
| `REPODY_BACKEND_EXTRAS` | Backend Python extras (default `otel`; see `backend/pyproject.toml`) |

Build cache: local builds reuse Docker's build cache; CI passes `--set <target>.cache-from/cache-to` (see `.github/workflows/images-ghcr.yml`).

## Local Compose

`pnpm platform setup` (and `pnpm platform dev`) copies `deploy/env/compose.env.example` to `backend/.env`.

Use these runtime overrides for local API/UI work:

| Variable | Description |
|----------|-------------|
| `REPODY_DEV_API_RELOAD` | Set `1` to opt into Uvicorn reload on Windows (`pnpm platform dev`) |
| `AUDIT_LLAMACPP_BASE_URL` | External OpenAI-compatible root, e.g. `http://127.0.0.1:8081/v1` |
| `AUDIT_LLAMACPP_SERVED_MODEL` | Model id from `/v1/models` |

Bugsink: `BUGSINK_DSN` in the runtime Secret (the web pod also exposes it as `NEXT_PUBLIC_BUGSINK_DSN`).
