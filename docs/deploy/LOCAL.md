# Local development (Compose)

Fast path for API, UI, OIDC, Taskiq workers, migrations, and extraction.

Official references:

- [Docker Compose](https://docs.docker.com/compose/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)
- [MinIO Docker](https://min.io/docs/minio/container/index.html)
- [Keycloak containers](https://www.keycloak.org/server/containers)

## Prerequisites

```powershell
corepack enable
pnpm install
pnpm doctor
docker compose version
```

Configure NuExtract once: copy `deploy\llamacpp\paths.local.env.example` → `deploy\llamacpp\paths.local.env` (model + mmproj paths, **`LLAMACPP_PORT=8081`**).

## First run

```powershell
pnpm dev:setup
```

Creates `backend/.env`, `.env.local`, starts Compose, runs migrations.

## Daily workflow

**One terminal (recommended):**

```powershell
pnpm dev:all
```

**Two terminals (split logs):**

```powershell
pnpm dev        # background: Compose + workers + NuExtract
pnpm dev:app    # foreground: API (:8000 by default) + UI (:3000)
```

Taskiq workers run as **Linux Compose services** (`--profile workers`) — worker processes use Redis from the Compose stack.

| Service | URL | Notes |
|---------|-----|--------|
| UI | http://localhost:3000 | |
| API | http://localhost:8000 | |
| Postgres | `localhost:5432` | Repody app DB |
| Redis | `localhost:6379` | Taskiq broker + cache |
| MinIO API | http://localhost:9000 | |
| MinIO console | http://localhost:9001 | `minioadmin` / `minio-local-dev` |
| Keycloak | http://localhost:8080 | admin / admin · realm `repody` |
| NuExtract | http://localhost:8081 | llama-server (host; workers use `host.docker.internal`) |
| Grafana | http://localhost:3030 | `pnpm dev:all` (default) or `pnpm dev:observability` |
| Bugsink | http://localhost:8090 | admin@repody.local / repody-dev (observability profile) |
| OTLP | http://localhost:4318 | traces from API/workers |

Sign in to Repody: `operator@repody.local` / `repody-dev` (use **localhost**, not `127.0.0.1`, for auth).

**Observability:** `pnpm dev:all` starts Grafana, Loki, Tempo, OTEL, and Bugsink by default (`-- --no-obs` to skip). JSON logs ship to Loki; traces correlate via `trace_id`. Restart the API after first enable. See [docs/OBSERVABILITY.md](../OBSERVABILITY.md).

**Pools:** runs **with uploaded PDFs** use the **extract** pool (NuExtract). Runs without files use **fast**. `pnpm dev` starts both workers by default.

The API port defaults to **8000**. If Windows keeps a stale listener after a killed
dev process, use a temporary fallback:

```powershell
$env:REPODY_API_PORT="8002"
pnpm dev:api
```

On Windows, API reload is disabled by default to avoid stale Uvicorn sockets. Set
`REPODY_DEV_API_RELOAD=1` only when you specifically need reload behavior.

## Operations

```powershell
pnpm dev:status     # what's up?
pnpm dev:restart    # after Vulkan ErrorDeviceLost
pnpm dev:stop       # stop API, UI, NuExtract, and Compose
pnpm llamacpp:verify
pnpm test:api
```

### NuExtract tuning (Intel Arc / Vulkan)

Repody local default: **`NuExtract3-Q4_K_M.gguf`** with alias `nuextract3-q4_k_m` (see `deploy/llamacpp/paths.local.env.example`).

Keep these in sync:

- `deploy/llamacpp/paths.local.env` → `LLAMACPP_MODEL_ALIAS`
- `backend/.env` → `AUDIT_LLAMACPP_SERVED_MODEL`
- `compose.yaml` → `worker-extract` `AUDIT_LLAMACPP_SERVED_MODEL`

Tuned defaults in `paths.local.env` when `LLAMACPP_DEVICE=Vulkan0`:

- **`LLAMACPP_IMAGE_MIN_TOKENS=1024`** / **`LLAMACPP_IMAGE_MAX_TOKENS=1024`** — Qwen-VL accuracy floor + fixed vision budget (unbounded max → Arc `ErrorDeviceLost`)
- **`LLAMACPP_UBATCH_SIZE=1024`** / **`LLAMACPP_MTMD_BATCH_MAX_TOKENS=1024`** — match the vision token budget
- **`LLAMACPP_PARALLEL=1`** — one slot, full 16k context
- PDF rasterization is fixed in code at **170 DPI** PNG (`nuextract_contract.py`)

After changes: `pnpm llamacpp:restart` and `pnpm dev:restart`.

### Extract run timeouts

Audit tasks are capped at **3 minutes** end-to-end. Keep these aligned in `backend/.env` (see `deploy/env/compose.env.example`):

| Variable | Local default | Role |
|----------|---------------|------|
| `AUDIT_WORKER_TASK_TIMEOUT_MINUTES` | 3 | Taskiq + worker hard kill (max 3) |
| `AUDIT_REPODY_VLM_TIMEOUT_SECONDS` | 180 | VLM HTTP ceiling (must be ≤ worker) |
| `AUDIT_STALE_RUN_TIMEOUT_MINUTES` | 5 | Maintenance reap for stuck `running` |

Runs that exceed 3 minutes fail with **"task timeout"**. Keep documents small (page count, DPI) so extraction fits the window.

On Linux/macOS you may use `pnpm dev:worker:native` instead of Compose workers.

## Verify

```powershell
pnpm dev:status
curl http://localhost:8000/v1/healthz
```

`taskiqConfigured` should be `true` in `/v1/healthz` when `AUDIT_REDIS_URL` is set and workers are running.

## Stop

```powershell
pnpm dev:stop
```

Full reset: `pnpm dev:stop -- --volumes` (or `docker compose down -v`).

## When you need a cluster

Use OpenShift client install or CRC lab verification — [OPENSHIFT.md](./OPENSHIFT.md). Daily work stays on Compose.
