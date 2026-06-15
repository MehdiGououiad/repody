# Environment variables

Single reference for secrets and `AUDIT_*` configuration across Compose, VPS, and Helm.

**Files:** repo-root `.env` (local + VPS after `deploy/cloud/setup-env.sh`), `.env.local` (Next.js host dev), `deploy/repody-vlm.env.example` (external vLLM).

## Required for production Compose / VPS

| Variable | Purpose |
|----------|---------|
| `AUDIT_ADMIN_API_TOKEN` | Admin API auth (api + web server-side) |
| `AUDIT_MINIO_PUBLIC_ENDPOINT` | Hostname browsers use for presigned uploads (e.g. `files.example.com`) |
| `POSTGRES_PASSWORD` | Postgres |
| `MINIO_ROOT_PASSWORD` | MinIO |

VPS also needs `PUBLIC_DOMAIN`, `FILES_DOMAIN`, and Caddy `BASIC_AUTH_*` — see [DEPLOY.md](../DEPLOY.md#ubuntu-vps).

## Inference (Repody VLM)

| Variable | Default (CPU) | Notes |
|----------|---------------|-------|
| `AUDIT_INFERENCE_MODE` | `docker_model_runner` | Set `vllm` for GPU / external vLLM |
| `AUDIT_REPODY_VLM_MODEL` | `repody/repody-vlm:q4_k_m-16k` | Docker Model Runner tag |
| `AUDIT_VLLM_BASE_URL` | — | Required when `AUDIT_INFERENCE_MODE=vllm` |
| `AUDIT_VLLM_SERVED_MODEL` | `numind/NuExtract3` | vLLM model id |

## Platform behavior

| Variable | Prod default | Description |
|----------|--------------|-------------|
| `AUDIT_SEED_ON_STARTUP` | `false` | Demo data on API boot |
| `AUDIT_RUN_MIGRATIONS_ON_STARTUP` | `true` | Alembic on API start |
| `AUDIT_AUTH_ENABLED` | `true` (api) | API token auth |
| `AUDIT_DIRECT_UPLOAD_ENABLED` | `true` | Presigned MinIO uploads |
| `AUDIT_STORAGE_BACKEND` | `s3` | MinIO in Compose |
| `AUDIT_LOG_JSON` | `true` (Helm) | Structured logs |
| `AUDIT_CORS_ORIGINS` | JSON array | Browser origins |

## Workers

| Variable | Default | Service |
|----------|---------|---------|
| `AUDIT_WORKER_OCR_MAX_JOBS` | `1` | `worker` |
| `AUDIT_WORKER_FAST_MAX_JOBS` | `8` | `worker-fast` |

## Optional modules

| Variable | Module | Description |
|----------|--------|-------------|
| `BUGSINK_SECRET_KEY` | `--with=bugsink` | Django secret (≥50 chars; `openssl rand -base64 50`) |
| `BUGSINK_DB_PASSWORD` | `--with=bugsink` | Postgres password for Bugsink DB |
| `BUGSINK_SUPERUSER` | `--with=bugsink` | Initial admin `email:password` (first boot only) |
| `BUGSINK_BASE_URL` | `--with=bugsink` | Public Bugsink URL (default `http://localhost:8090`) |
| `BUGSINK_DSN` | api, workers | Sentry-compatible DSN for backend |
| `NEXT_PUBLIC_BUGSINK_DSN` | web build | Browser DSN (baked at build time) |
| `AUDIT_DEV_OBS` | dev recipes | `none` \| `logs` \| `traces` for local Grafana |

## CI / image build

| Variable | Purpose |
|----------|---------|
| `REPODY_IMAGE_REGISTRY` | e.g. `ghcr.io/org` (no trailing slash) |
| `REPODY_IMAGE_TAG` | Image tag (`latest` default) |

Used by `prod-micro` stack and `pnpm images:build`.

## Hatchet

Token is written by the `hatchet-init` one-shot (`profiles: [init]`). Mounted at `/shared/hatchet.token` — no manual `HATCHET_CLIENT_TOKEN` in dev.

## Helm parity

Helm maps the same keys via `deploy/helm/repody/templates/configmap.yaml` and `values.yaml`. Run `pnpm deploy:check` after changing production defaults.
