# Production deployment

Deploy the full platform as production Docker images — no bind mounts, no hot reload.

**Cloud VPS (share with users over HTTPS):** see [DEPLOY-CLOUD.md](./DEPLOY-CLOUD.md).

## Prerequisites

- Docker Desktop / Engine with **BuildKit** enabled (default on Docker Desktop)
- ~16 GB RAM recommended for CPU stack (Docker Model Runner + Repody VLM)
- Ports: `3000` (web), `8000` (api), `5432`, `6379`, `8888` (Hatchet UI), `7077` (Hatchet gRPC), `9000`

## CPU stack (default)

```powershell
pnpm docker:deploy
```

Equivalent to:

```powershell
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml --profile web up -d --build
```

This starts:

| Service | Role |
|---------|------|
| postgres | Database |
| redis | Cache, SSE pub/sub, rate limits |
| hatchet-lite | Workflow orchestration (audit runs) |
| minio | Document storage (S3-compatible) |
| model-runner | Docker Model Runner (Repody VLM GGUF) |
| api | FastAPI (2 workers, no reload) |
| worker | Hatchet worker pool `ocr` (document model extraction) |
| worker-fast | Hatchet worker pool `fast` (logic-only / no-file runs) |
| web | Next.js production standalone |

## GPU stack (Repody VLM via vLLM)

GPU deployment uses vLLM with Repody VLM weights (see [docs/REPODY-VLM.md](./docs/REPODY-VLM.md)):

- **CPU path:** Docker Model Runner → llama.cpp GGUF (`pnpm docker:deploy`)
- **GPU path:** vLLM OpenAI server with MTP speculative decoding (`pnpm docker:deploy:gpu`)

```powershell
pnpm docker:verify:gpu   # validate compose merge (no GPU needed)
pnpm docker:deploy:gpu
```

File chain:

```powershell
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.gpu.yaml -f compose.prod.yaml --profile web up -d --build
```

The `vllm` service runs the official command (non-thinking mode, MTP enabled). API and workers use `AUDIT_INFERENCE_MODE=vllm`.

**Important:** `compose.gpu.yaml` is an overlay on `compose.cpu.yaml` — never deploy GPU without the CPU base file.

### GPU prerequisites

- NVIDIA GPU + drivers
- Docker Compose GPU support
- ~16 GB+ VRAM recommended for Repody VLM
- First boot downloads Hugging Face weights into the `vllm_cache` volume

### Adding more document models

Register each catalog id in `backend/src/audit_workbench/extraction/model_registry.py` with its own `runtime` and `runtime_model`.

### Verify on GPU hardware

```powershell
curl http://localhost:8000/v1/healthz
curl "http://localhost:8000/v1/diagnostics/ocr?run_infer=true"
pnpm test:platform:integration
```

LLM rule validation still uses Docker Model Runner unless you configure a separate validation model.

## With observability

```powershell
pnpm docker:deploy:obs
```

Adds Grafana (port 3001), Loki, and Promtail. See [docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md).

## Verify deployment

```powershell
curl http://localhost:8000/v1/healthz
curl http://localhost:3000
```

**New-environment integration suite** (health, catalogs, presign upload, Repody VLM cold/warm, logic pass/fail):

```powershell
pnpm test:platform:integration
```

Full platform verification (integration suite + live pytest + Playwright):

```powershell
pnpm test:platform
```

Unit and in-process API tests (no running stack required):

```powershell
pnpm test:api
pnpm test:api:e2e
```

Live stack tests (requires `pnpm docker:deploy`):

```powershell
pnpm test:api:live
pnpm test:facture:stack
```

## Production vs development compose files

| File | Purpose |
|------|---------|
| `compose.yaml` | Base services |
| `compose.cpu.yaml` | Repody VLM + Docker Model Runner CPU tuning |
| `compose.gpu.yaml` | vLLM Repody VLM service + `AUDIT_INFERENCE_MODE=vllm` |
| `compose.e2e.yaml` | CI Playwright smoke (stub extraction, seed data) |
| `compose.dev.yaml` | Fast dev: bind mounts, warmup off, compose watch |
| `compose.prod.yaml` | Production: no bind mounts, restart policies, 2 API workers |
| `compose.scale.yaml` | Horizontal scale: DB pool, worker tuning |
| `compose.observability.yaml` | Grafana/Loki (`--profile obs`) |

## Environment variables

Set production secrets via a `.env` file in the project root (read by Docker Compose) or export before deploy:

```env
# Example overrides — do not commit real secrets
POSTGRES_PASSWORD=change-me
AUDIT_REPODY_VLM_MODEL=agentcontrol/repody-vlm:q4_k_m-16k
AUDIT_LLM_VALIDATION_ENABLED=false
```

Key production defaults in `compose.prod.yaml`:

- `AUDIT_SEED_ON_STARTUP=false` — no demo seed data
- `AUDIT_REPODY_VLM_WARMUP_ON_START=true` — warm Repody VLM on boot
- API runs with `--workers 2` (no `--reload`)
- Source code is baked into images (no `./backend/src` bind mount)

## Updating a running deployment

```powershell
# Pull latest code, then:
pnpm docker:deploy          # rebuilds changed layers only (BuildKit cache)
```

Rebuild a single service:

```powershell
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml build api
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml up -d api
```

## Image build optimizations

Dockerfiles use:

- **Layer caching** — Python deps install before source copy (`backend/Dockerfile`)
- **BuildKit cache mounts** — `uv` and `pnpm` store caches persist between builds
- **Multi-stage web build** — `Dockerfile.web` produces minimal standalone Next.js image

Enable BuildKit if needed:

```powershell
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
```

(`scripts/docker.mjs` sets these automatically.)

## Horizontal scaling (multi-user)

Phase 2 adds production scaling knobs. Default deploy still runs **1 OCR worker** — scale explicitly for concurrent users.

### Scale OCR workers

Each OCR replica runs **1 document-model job** at a time. Add replicas:

```powershell
pnpm docker:deploy:scale
```

Equivalent to deploy + `compose.scale.yaml` + `--scale worker=2`.

Custom replica count:

```powershell
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml -f compose.scale.yaml up -d --scale worker=3
```

Tune per-replica concurrency via env:

| Variable | Default | Role |
|----------|---------|------|
| `AUDIT_WORKER_OCR_MAX_JOBS` | `1` | OCR worker (keep at 1 on CPU) |
| `AUDIT_WORKER_FAST_MAX_JOBS` | `8` | Fast worker pool (text-only runs) |

### Worker scaling

Each OCR replica runs one document-model job at a time. Add replicas:

```powershell
pnpm docker:deploy:scale
```

### Direct uploads (presigned MinIO)

Production API uses **presigned PUT URLs** so the browser uploads PDFs directly to MinIO — the API never buffers 25 MB files in memory.

- `GET /v1/uploads/capabilities` — check `directUploadEnabled`
- `POST /v1/uploads/presign` → client PUT → `POST /v1/uploads/confirm`
- `POST /v1/workflows/{id}/runs/json` — start run with storage keys

Set `AUDIT_MINIO_PUBLIC_ENDPOINT=localhost:9000` (or your public MinIO host) so presigned upload URLs work from the browser.

### Database & Redis pools

| Variable | Default (prod) | Purpose |
|----------|----------------|---------|
| `AUDIT_DB_POOL_SIZE` | `10` | Connections per API/worker process |
| `AUDIT_DB_MAX_OVERFLOW` | `20` | Burst connections |
| `AUDIT_REDIS_MAX_CONNECTIONS` | `32` | Shared pool for cache + SSE |

## Phase 3 — Platform hardening

### Structured LLM (instructor + Pydantic)

When `AUDIT_STRUCTURED_LLM_ENABLED=true`, LLM rule evaluation can use Pydantic-validated JSON
via the Docker Model Runner OpenAI-compatible endpoint (requires `AUDIT_LLM_VALIDATION_ENABLED=true`).

### Production logging

```env
AUDIT_LOG_JSON=true
```

Enabled by default in `compose.prod.yaml`.

### OpenTelemetry

Install the otel extra and enable tracing:

```env
AUDIT_OTEL_ENABLED=true
AUDIT_OTEL_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces
```

Instruments FastAPI, httpx, and SQLAlchemy when `audit-workbench[otel]` is installed.

### Rate limiting

Redis-backed limits on run creation:

| Variable | Default |
|----------|---------|
| `AUDIT_RATE_LIMIT_RUNS_PER_WORKFLOW` | 30 / minute |
| `AUDIT_RATE_LIMIT_RUNS_PER_CLIENT` | 120 / minute |

Returns HTTP 429 when exceeded. Skipped when `AUDIT_RUN_JOBS_INLINE=true`.

### Hatchet workflow orchestration

Audit runs are dispatched to **Hatchet** (`audit-run` workflow). Workers register with `pool: fast|ocr` labels.

| Variable | Default | Role |
|----------|---------|------|
| `HATCHET_CLIENT_TOKEN` | (from init) | API + worker auth |
| `HATCHET_CLIENT_HOST_PORT` | `hatchet-lite:7077` | gRPC engine |
| `HATCHET_CLIENT_TLS_STRATEGY` | `none` | TLS for hatchet-lite |
| `AUDIT_WORKER_POOL` | `ocr` | Worker label (`fast` or `ocr`) |

Hatchet UI: http://localhost:8888 (after `pnpm docker:deploy`).

Token bootstrap: `hatchet-init` service writes `/shared/hatchet.token`, loaded by entrypoint.
Manual fallback: `python backend/scripts/hatchet_create_token.py --out .env.hatchet.token`

## Stopping

```powershell
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml --profile web down
```

Add `-v` only if you intend to wipe database and model volumes.

## Share Repody with users

The web UI has **no per-user login**. The Next.js server injects the admin API token on every `/api/*` request, so anyone who can open the app URL has **full platform access**. Protect the URL (basic auth, VPN, or private network).

### Option A — Same Wi‑Fi / office LAN (quickest)

```powershell
pnpm docker:configure:lan   # writes PUBLIC_HOST + MinIO endpoint to .env
pnpm docker:deploy:lan      # recreates api, web, minio with LAN CORS
```

Share with teammates: `http://<PUBLIC_HOST>:3000` (shown by configure-lan).

- Allow inbound **TCP 3000** and **9000** in Windows Firewall (or your host firewall).
- Uploads use presigned URLs to `http://<PUBLIC_HOST>:9000` — both ports must be reachable.

### Option B — Public HTTPS domain

1. Point DNS `A` records for `app.example.com` and `files.example.com` to your server.
2. Add to `.env`:

```env
PUBLIC_DOMAIN=app.example.com
FILES_DOMAIN=files.example.com
BASIC_AUTH_USER=repody
BASIC_AUTH_HASH=<run: docker run --rm caddy:2-alpine caddy hash-password>
```

3. Deploy:

```powershell
pnpm docker:deploy:public
```

Users open `https://app.example.com`, enter the basic-auth password, then use Repody normally.

Caddy terminates TLS and proxies:

| Host | Backend |
|------|---------|
| `PUBLIC_DOMAIN` | Next.js web (`:3000`) |
| `FILES_DOMAIN` | MinIO (`:9000`) for browser uploads |

### Option C — Programmatic API per workflow

In the UI: open a workflow → **Deploy** → copy the workflow **API key**. External systems call the run endpoints with `Authorization: Bearer <workflow-api-key>` (no UI access).

### Scaling for multiple concurrent users

```powershell
pnpm docker:deploy:scale   # adds OCR worker replicas
```

## Checklist before go-live

- [ ] Change default postgres/minio/grafana passwords
- [ ] Set `AUDIT_SEED_ON_STARTUP=false`
- [ ] Configure real S3 instead of MinIO if needed (`AUDIT_STORAGE_BACKEND=s3`)
- [ ] Set `AUDIT_CORS_ORIGINS` to your domain
- [ ] Put reverse proxy (nginx/Caddy) with TLS in front of ports 3000/8000
- [ ] Run `pnpm test:platform:integration` against the deployed stack
- [ ] Run `pnpm test:platform` for full browser + API verification
- [ ] Enable observability profile for log retention
