# Environment variables

The API and the worker read every `AUDIT_*` variable through one model,
[`backend/src/repody/settings.py`](../backend/src/repody/settings.py); anything unset uses the
default there. Locally, copy `deploy/env/compose.env.example` to `backend/.env` (and
`deploy/env.auth.example` to `.env.local` for Better Auth). On Kubernetes the Helm chart renders
`config` into a ConfigMap and reads credentials from the `existingSecret`
([docs/CLUSTER.md](../docs/CLUSTER.md#2-runtime-secret)). List values (`AUDIT_CORS_ORIGINS`,
`AUDIT_OIDC_ISSUER_ALIASES`, `AUDIT_UPLOAD_ALLOWED_MIME_TYPES`) are comma-separated.

## Services

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_DATABASE_URL` | local Postgres | `postgresql+asyncpg://…` (secret) |
| `AUDIT_DB_POOL_SIZE` | `10` | Connections per process |
| `AUDIT_REDIS_URL` | `redis://localhost:6379/0` | Task queue, rate limits, extraction cache (secret) |
| `AUDIT_S3_ENDPOINT_URL` | `http://localhost:9000` | S3-compatible storage for uploaded documents |
| `AUDIT_S3_ACCESS_KEY` / `AUDIT_S3_SECRET_KEY` | Compose: SeaweedFS dev keys | Storage credentials (secret) |
| `AUDIT_S3_BUCKET` | `audit-documents` | Created at API start when missing |

## Platform

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_DEPLOYMENT_ENVIRONMENT` | `development` | `production` requires OIDC |
| `AUDIT_DEBUG` | `false` | Debug log level |
| `AUDIT_LOG_JSON` | `true` | JSON log lines (`false`: console) |
| `AUDIT_CORS_ORIGINS` | empty (no CORS) | Browser apps on other origins that call the API directly (the web app goes through its own server) |
| `AUDIT_SEED_ON_STARTUP` | `false` | Load the demo workflow at API start |
| `AUDIT_RUN_MIGRATIONS_ON_STARTUP` | `false` | Container entrypoint runs `alembic upgrade head` first |

## Auth (Keycloak)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_OIDC_ENABLED` | `false` | Require Keycloak tokens (off: every caller is a local admin) |
| `AUDIT_OIDC_ISSUER` | — | Realm URL, e.g. `https://auth.example.com/realms/repody` |
| `AUDIT_OIDC_ISSUER_ALIASES` | — | The same realm under other host names |
| `AUDIT_OIDC_AUDIENCE` | — | Expected `aud` (client id); unset: not checked |
| `AUDIT_OIDC_JWKS_URL` | `{issuer}/protocol/openid-connect/certs` | Signing keys |

## Uploads and inference

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_MAX_UPLOAD_BYTES` | 25 MiB | Per file |
| `AUDIT_MAX_UPLOAD_FILES` | `20` | Per run |
| `AUDIT_UPLOAD_ALLOWED_MIME_TYPES` | PDF, PNG, JPEG, WebP | Checked on the file's bytes |
| `AUDIT_LLAMACPP_BASE_URL` | `http://127.0.0.1:8081/v1` | OpenAI-compatible llama-server serving NuExtract |
| `AUDIT_LLAMACPP_API_KEY` | `local` | Bearer token for the endpoint (secret) |
| `AUDIT_LLAMACPP_SERVED_MODEL` | `nuextract3-q8_0` | Model id from `/v1/models` |
| `AUDIT_MARKDOWN_PROVIDER` | `nuextract` | Markdown for documents without fields: `nuextract` or `lightonocr` |
| `AUDIT_LIGHTONOCR_BASE_URL` | `http://127.0.0.1:8082/v1` | OpenAI-compatible server for LightOnOCR-3 (`pnpm lightonocr:serve`) |
| `AUDIT_LIGHTONOCR_API_KEY` | `local` | Bearer token for that endpoint (secret) |
| `AUDIT_LIGHTONOCR_SERVED_MODEL` | `lightonocr-3-4b` | LightOnOCR model id from `/v1/models` |
| `AUDIT_INFERENCE_TIMEOUT_SECONDS` | `180` | Per model call; must fit in the run timeout |
| `AUDIT_LLAMACPP_PROBE` | `true` | `false` for an endpoint that scales to zero: Settings then shows the model as on demand instead of waking it |
| `AUDIT_INFERENCE_CONCURRENCY` | `1` | Model requests in flight per process: set to llama-server `--parallel`; documents and pages are sent concurrently up to it |
| `AUDIT_MAX_PAGES_PER_DOCUMENT` | all | Cap pages sent to the model (match `--limit-mm-per-prompt`) |
| `AUDIT_EXTRACTION_CACHE_TTL_SECONDS` | `0` | Cache model answers in Redis (`0` = off) |

## Runs

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_WORKER_CONCURRENCY` | `1` | Runs per worker container: the image passes it to `taskiq worker --max-async-tasks` |
| `AUDIT_RUN_TIMEOUT_MINUTES` | `5` | A longer run fails; a `running` run past it is failed by maintenance |
| `AUDIT_MAX_QUEUED_RUNS` | `200` | Starting a run answers 503 beyond this (`0` = no cap) |
| `AUDIT_RUNS_PER_MINUTE_PER_CLIENT` | `600` | Per API key or user (`0` = no limit) |
| `AUDIT_MAINTENANCE_INTERVAL_SECONDS` | `60` | How often the scheduler sends the maintenance task (fail stuck runs, resend lost tasks, purge expired runs) |
| `AUDIT_RUN_RETENTION_DAYS` | `0` | Delete finished runs (and their uploaded files) older than this (`0` = keep) |

## Observability

| Variable | Purpose |
|----------|---------|
| `OTEL_SDK_DISABLED=false` | Start the OpenTelemetry agent (traces); `OTEL_*` configure it |
| `SENTRY_DSN` | Send errors to Bugsink (Sentry SDK); the Helm chart maps it from `BUGSINK_DSN` |
