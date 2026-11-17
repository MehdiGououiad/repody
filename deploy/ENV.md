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
| `HATCHET_CLIENT_TOKEN` | — | Hatchet API token: the run queue and the maintenance cron (secret). Compose: written by `pnpm platform` (local) or the `hatchet-token` service (VPS) |
| `HATCHET_CLIENT_HOST_PORT` / `HATCHET_CLIENT_SERVER_URL` | from the token | Hatchet's gRPC address and API URL, when the token's are not reachable from the container |
| `HATCHET_CLIENT_TLS_STRATEGY` | `tls` | `none` for an engine on a private network without TLS (Compose) |
| `AUDIT_S3_ENDPOINT_URL` | `http://localhost:9000` | S3-compatible storage for uploaded documents |
| `AUDIT_S3_ACCESS_KEY` / `AUDIT_S3_SECRET_KEY` | Compose: SeaweedFS dev keys | Storage credentials (secret) |
| `AUDIT_S3_BUCKET` | `audit-documents` | Created at API start when missing |

## Platform

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_DEPLOYMENT_ENVIRONMENT` | `development` | `production` and `staging` require OIDC |
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
| `AUDIT_MAX_REQUEST_BYTES` | 100 MiB | A whole upload request (all files and fields), counted as it arrives; keep the web app's `proxyClientMaxBodySize` (`next.config.ts`) at the same size |
| `AUDIT_UPLOAD_ALLOWED_MIME_TYPES` | PDF, PNG, JPEG, WebP | Checked on the file's bytes |
| `AUDIT_LLAMACPP_BASE_URL` | `http://127.0.0.1:8081/v1` | OpenAI-compatible llama-server serving NuExtract |
| `AUDIT_LLAMACPP_API_KEY` | `local` | Bearer token for the endpoint (secret) |
| `AUDIT_LLAMACPP_SERVED_MODEL` | `nuextract3-q8_0` | Model id from `/v1/models` |
| `AUDIT_INFERENCE_TIMEOUT_SECONDS` | `180` | Per model call; must fit in the run timeout |
| `AUDIT_LLAMACPP_PROBE` | `true` | `false` for an endpoint that scales to zero: Settings then shows the model as on demand instead of waking it |
| `AUDIT_INFERENCE_CONCURRENCY` | `1` | Model requests in flight per process: set to llama-server `--parallel`; documents and pages are sent concurrently up to it |
| `AUDIT_MAX_PAGES_PER_DOCUMENT` | all | Cap pages sent to the model (match `--limit-mm-per-prompt`) |
| `AUDIT_MAX_PAGES_PER_RUN` | all | Pages one run may send the model, all its documents together; checked from the files before the run is queued (422) |
| `AUDIT_MAX_OUTPUT_TOKENS` | `16384` | The longest answer the model may write. A schema without tables or lists gets less, by its size, so an answer that loops stops early |
| `AUDIT_MAX_JSON_BYTES` | 2 MiB | Every other request body (workflow definitions), counted as it arrives, with or without a Content-Length; larger ones get 413 |

## Runs

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_WORKER_CONCURRENCY` | `4` | Runs one worker takes at once (its Hatchet slots) |
| `AUDIT_RUN_TIMEOUT_MINUTES` | `5` | Hatchet's execution timeout: a longer run is cancelled and failed. A run that waits over an hour for a worker fails too |
| `AUDIT_MAX_QUEUED_RUNS` | `200` | Starting a run answers 503 beyond this (`0` = no cap) |
| `AUDIT_RUNS_PER_MINUTE_PER_CLIENT` | `600` | Runs one API key or user starts a minute; more wait their turn in Hatchet (`0` = no limit) |
| `AUDIT_RUNS_IN_PROGRESS_PER_CLIENT` | `2` | Runs one API key or user has in progress at once; clients take turns (Hatchet round robin) |
| `AUDIT_RUN_RETENTION_DAYS` | `0` | Delete finished runs (and their uploaded files) older than this (`0` = keep); the maintenance cron runs every minute |

## Credits

Every run is metered: 1 credit = 1 page sent to the model, plus `AUDIT_CREDIT_RUN_FEE` per run.
A run holds its estimate (its files' pages) when it is queued. It then pays the pages it sent
when done, its estimate when it failed after it started or the model failed on a document, and
nothing when it never started. Usage per account: `GET /v1/credits/usage?since=&until=`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_CREDITS_ENFORCED` | `false` | Refuse a run (402) when its account cannot pay its estimate. Off: runs are metered, never refused (an on-premise installation) |
| `AUDIT_CREDIT_RUN_FEE` | `0` | Credits per run on top of its pages: the GPU's start and idle time a run causes on a model that scales to zero |

**Accounts.** A client company is a Keycloak group named `client-<name>`. Its users see and change
only its workflows, runs and audits, and its credits pay their runs and its workflows' API-key runs.
Users outside any client group (every user of a single-client installation) and `platform_admin`
see everything; their workflows are shared: every client reads and duplicates them, none edits or
runs them. Their runs are charged to the `deployment` account, which is metered and never refused.

**Granting.** A `platform_admin` grants credits (a negative amount takes them back):

```bash
curl -X POST https://<app>/api/v1/credits/grants -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -d '{"account": "client-acme", "amount": 200, "note": "trial"}'
```

**Sizing for the Modal GPU** (measured in deploy/modal/README.md: about 10 s per page at worst,
Markdown; 1–4 s for a field extraction; about 75 s of start and idle time per isolated run). With
`AUDIT_CREDIT_RUN_FEE=8`, 200 credits cost at most about $1 on an L4 ($0.80/h) and $1.20 on an A10
($1.10/h), for Markdown-only runs. Field extraction costs a fraction of that.

**Keycloak setup.** The realm files map group membership into the access token (`groups`, the
`repody-web` client) and the production realm sets a password policy. A realm imported before
that has neither: add them once in the admin console:
1. Clients → `repody-web` → Client scopes → `repody-web-dedicated` → Add mapper → By configuration →
   Group Membership. Name and token claim name `groups`, Full group path off, Add to access token on.
2. Realm settings → Policies → Password policy: Minimum length 12, Not username, Password history 3.
3. Groups → Create group `client-<name>` per client, and add its users (with the `operator` or
   `admin` role).

## Admin area

Platform admins manage client companies in Repody (**Admin** in the sidebar): create a client
(its Keycloak group), invite its users with a one-time password, change their role, disable or
remove them, give credits, hand a workflow to a client, see this month's GPU spend, and read the
audit log of every change. Keycloak stays the source of truth for users and passwords.

Repody reaches Keycloak as the `repody-admin` service account (client credentials). It holds only
realm-management's `manage-users`, `view-users`, `query-users` and `query-groups`, and the
`kc-admin-api` client scope Keycloak 26.8.2+ requires for the Admin API. Repody only ever gives a
client role (viewer, operator, admin) and never edits a platform admin; Keycloak itself would let
this account grant any realm role, so keep its secret like the others.

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_KEYCLOAK_ADMIN_CLIENT_SECRET` | — | The `repody-admin` client's secret; without it, Admin shows credits and spend but cannot manage clients |
| `AUDIT_REQUIRE_CLIENT_GROUP` | `false` | `true` on an installation shared by several client companies (the hosted demo): a user in no `client-*` group who is not a platform admin gets no permission instead of seeing everything |
| `AUDIT_KEYCLOAK_ADMIN_CLIENT_ID` | `repody-admin` | |
| `AUDIT_KEYCLOAK_INTERNAL_ISSUER` | `AUDIT_OIDC_ISSUER` | The realm as the API reaches it, e.g. `http://keycloak:8080/realms/repody` |
| `AUDIT_CREDIT_LOW_BALANCE` | `20` | Admin flags a client below this; its users see a warning banner |
| `AUDIT_GPU_DOLLARS_PER_HOUR` | `1.10` | For Admin's spend estimate (model time × this) |

**New installation:** the realm files create `repody-admin` with the secret
`KEYCLOAK_ADMIN_CLIENT_SECRET` (VPS `.env`, `openssl rand -hex 32`). **A realm imported before
1.5:** set `KEYCLOAK_ADMIN_CLIENT_SECRET` in `.env`, deploy, then run once on the server, from
`/opt/repody`: `sh setup-admin-client.sh` (copied from `deploy/keycloak/`). It is safe to run
again.

## Access requests

The site's contact form (repody.com) sends access requests to `POST /api/v1/access-requests`, the
one API route open without a session. A platform admin approves them in Admin, Access requests:
that creates the client (or reuses it), invites the person with a one-time password and gives
starting credits. Each request needs a Cloudflare Turnstile token (when the secret is set) and the
consent box; one network sends at most `AUDIT_ACCESS_REQUESTS_PER_HOUR` (a SHA-256 of its address
is stored, never the address).

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_ACCESS_REQUESTS_ENABLED` | `false` | Take requests at all (Repody's own installation, behind its site). Off: the route answers 404, so a client's installation opens no public form |
| `AUDIT_TURNSTILE_SECRET` | — | Turnstile's secret key (widget `repody-access-requests`, site key in `site/lib/site.ts`); unset: no anti-robot check, which production and staging refuse to start with |
| `AUDIT_ACCESS_REQUESTS_PER_HOUR` | `5` | Requests one network may send an hour (429 beyond). The network is Cloudflare's `CF-Connecting-IP`: meaningful only behind Cloudflare, since anyone can set that header elsewhere |
| `AUDIT_ACCESS_REQUEST_RETENTION_DAYS` | `90` | Declined requests are deleted after this (the maintenance cron); the site's privacy page says so |
| `AUDIT_CORS_ORIGINS` | — | Must list the site's origin (`https://repody.com`), or browsers refuse the form's request |

## Observability

| Variable | Purpose |
|----------|---------|
| `OTEL_SDK_DISABLED=false` | Start the OpenTelemetry agent (traces); `OTEL_*` configure it |
| `SENTRY_DSN` | Send errors to Bugsink (Sentry SDK); the Helm chart maps it from `BUGSINK_DSN` |
