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

## NuExtract Cloud (platform API)

Catalog id: `repody:vlm:cloud`. Uses the official NuExtract REST API
([docs](https://nuextract.ai/doc)) — not local llama-server.

| Variable | Purpose |
|----------|---------|
| `AUDIT_NUEXTRACT_CLOUD_ENABLED=true` | Register NuExtract Cloud in the document model catalog |
| `AUDIT_NUEXTRACT_CLOUD_API_KEY` | Bearer API key (`Authorization: Bearer …`) |
| `AUDIT_NUEXTRACT_CLOUD_BASE_URL` | Default `https://nuextract.ai` |
| `AUDIT_NUEXTRACT_CLOUD_PROJECT_ID` | Optional fixed `sprj_…`; omit to create a temp project per request |
| `AUDIT_NUEXTRACT_CLOUD_TIMEOUT_SECONDS` | HTTP/SSE job timeout (default 180) |

Store the API key in secrets only — never commit it.

## Alternate document models (OCR)

| Variable | Purpose |
|----------|---------|
| `AUDIT_PADDLEOCR_V6_ENABLED` | Register `paddleocr:v6` in the catalog (markdown-only) |
| `AUDIT_PADDLEOCR_V6_BASE_URL` | PP-OCRv6 HTTP root, e.g. `http://127.0.0.1:8868` |
| `AUDIT_PADDLEOCR_V6_TIMEOUT_SECONDS` | Request timeout (default 180) |
| `AUDIT_PADDLEOCR_V6_USE_DOC_ORIENTATION_CLASSIFY` | Official `/ocr` override (default `true`; set `false` for already-oriented inputs) |
| `AUDIT_PADDLEOCR_V6_USE_DOC_UNWARPING` | Official `/ocr` override (default `true`; set `false` for clean documents) |
| `AUDIT_PADDLEOCR_V6_USE_TEXTLINE_ORIENTATION` | Official `/ocr` override (default `true`; set `false` for the documented fast path) |
| `AUDIT_PADDLEOCR_QWEN_ENABLED` | Register `paddleocr:qwen` (PP-OCRv6 + Qwen structured extraction) |
| `AUDIT_QWEN35_BASE_URL` | Qwen OpenAI API root, e.g. `http://127.0.0.1:8084/v1` |
| `AUDIT_QWEN35_SERVED_MODEL` | Qwen model alias (default `Qwen3.5-4B`) |
| `AUDIT_QWEN35_TIMEOUT_SECONDS` | Qwen text→JSON timeout (default 180) |
| `AUDIT_GLM_OCR_ENABLED` | Register `glm:ocr` in the catalog (markdown-only) |
| `AUDIT_GLM_OCR_BASE_URL` | OpenAI-compatible root, e.g. `http://127.0.0.1:8083/v1` |
| `AUDIT_GLM_OCR_SERVED_MODEL` | Model id / alias (default `GLM-OCR`) |
| `AUDIT_GLM_OCR_TIMEOUT_SECONDS` | Request timeout (default 180) |
| `AUDIT_GLM_OCR_LAYOUT_DEVICE` | PP-DocLayoutV3 device (`cpu` recommended with host llama) |
| `AUDIT_GLM_OCR_LAYOUT_MODEL_DIR` | Layout model id/path (default `PaddlePaddle/PP-DocLayoutV3_safetensors`) |
| `AUDIT_GLM_OCR_SDK_MAX_WORKERS` | Region OCR parallelism (default 1; keep ≤ llama-server `-np`) |
| `AUDIT_GLM_OCR_PDF_MAX_PAGES` | Optional PDF page cap; unset = official unlimited |
| `AUDIT_GLM_OCR_ID_CARD_PROFILE` | Optional ID-card profile (`config.idcard.yaml`); default `false` |
| `AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT` | Dual structured+markdown pass; default `false` (markdown-only still works per document) |
| `AUDIT_EXTRACTION_CACHE_ENABLED` | Redis extraction cache; default `false` |

Model HTTP timeouts must stay ≤ `AUDIT_WORKER_TASK_TIMEOUT_MINUTES * 60` (ceiling 15 min).
Compose extract defaults: worker **10** min, model timeouts **600** s, stale **12** min.

Local: `pnpm paddleocr:v6:serve` / `pnpm qwen35:serve` / `pnpm glmocr:serve` (OCR/GLM also started by `pnpm dev:all`). See [docs/PADDLEOCR-V6.md](../docs/PADDLEOCR-V6.md), [docs/GLM-OCR.md](../docs/GLM-OCR.md), and [docs/EXTRACTION.md](../docs/EXTRACTION.md).

## Platform agents

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_AGENT_IDP_ENABLED` | `true` | Run the IDP extract+validate stage; the recipe is empty without it |

IDP is the only agent ([ADR 007](../docs/adr/007-staged-agent-queues-taskiq.md)).

Helm values:

```yaml
config:
  inferenceMode: llamacpp
  llamacppBaseUrl: https://vlm.example.com/v1
  llamacppServedModel: numind/NuExtract3
  agentIdpEnabled: true
  paddleocrV6Enabled: false
  glmOcrEnabled: false

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
| `AUDIT_DISPATCH_REPLAY_BATCH_SIZE` | `100` | Outbox rows claimed per maintenance drain |
| `AUDIT_DISPATCH_KIQ_CONCURRENCY` | `16` | Parallel Taskiq kiq after claim batch |
| `AUDIT_QUEUE_REFRESH_SSE_LIMIT` | `32` | Max SSE publishes on maintenance queue refresh (`0` = DB-only) |
| `AUDIT_QUEUE_REFRESH_DB_LIMIT` | `128` | Max queued rows loaded/updated per maintenance tick |
| `AUDIT_OUTBOX_RETAIN_DISPATCHED_DAYS` | `7` | Purge dispatched outbox rows older than this |
| `AUDIT_DIRECT_UPLOAD_ENABLED` | `true` | Presigned object-storage uploads |
| `AUDIT_STORAGE_BACKEND` | `s3` | Object storage |
| `AUDIT_LOG_JSON` | `true` | Structured logs |
| `AUDIT_CORS_ORIGINS` | JSON array | Browser origins |

## Image Build

| Variable | Purpose |
|----------|---------|
| `REPODY_IMAGE_REGISTRY` | e.g. `ghcr.io/org`; required for `pnpm images:release` and `pnpm images:push` |
| `REPODY_IMAGE_TAG` | Image tag (`latest` default) |
| `REPODY_BACKEND_IMAGE_TAG` | Backend image tag override |
| `REPODY_WEB_IMAGE_TAG` | Web image tag override |
| `REPODY_WEB_BACKEND_URL` | Optional build-arg placeholder only (rewrites removed; runtime uses `INTERNAL_API_URL`) |
| `INTERNAL_API_URL` | Runtime web→API origin (Compose: `http://api:8000`, K8s: `http://repody-api:8000`) |
| `BACKEND_URL` | Fallback origin if `INTERNAL_API_URL` unset |
| `AUTH_KEYCLOAK_INTERNAL_ISSUER` | In-cluster Keycloak issuer for Auth.js server calls (Compose: `http://keycloak:8080/realms/repody`) |
| `REPODY_BACKEND_EXTRAS` | Backend Python extras (default `otel,glmocr`). `glmocr` pulls torch/torchvision from the **PyTorch CPU index** (see `backend/pyproject.toml` `tool.uv.sources`) so images match `AUDIT_GLM_OCR_LAYOUT_DEVICE=cpu`. Use `otel` only to slim. |
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
