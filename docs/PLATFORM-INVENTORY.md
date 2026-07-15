# Repody platform inventory

Complete reference for product features, architecture, security, performance, production setup, libraries, and tooling. For operational how-tos, see [COMMANDS.md](./COMMANDS.md). For architecture narrative and glossary, see [CONTEXT.md](../CONTEXT.md).

**Product:** Repody — enterprise document audit platform (configure workflows → upload documents → extract fields with a VLM → validate with rules → review in UI).

**Repo names:**

| Name | Where | Meaning |
|------|--------|---------|
| **Repody** | Product, npm, Helm | Public name |
| **repody** | `backend/pyproject.toml` | Python distribution |
| **audit_workbench** | `backend/src/audit_workbench/` | Python import path |

---

## 1. Product features

### Workflow configuration

- Workflow builder: documents, field schemas (types, descriptions, enums), extraction instructions, in-context learning (ICL) examples
- Rule library: reusable rule templates
- Logic rules: deterministic checks via `simpleeval` on extracted fields
- LLM rules: natural-language validation via a separate text model (not the VLM)
- Cross-document validation across multiple documents in one workflow
- Workflow deployment and activation for production runs
- Workflow API keys for run access without full admin JWT

### Document ingestion and extraction

- Presigned direct upload to MinIO/S3 (PDF, PNG, JPEG, WebP)
- MIME sniffing (`filetype`) vs declared content type
- PDF rasterization: PNG @ **170 DPI** (official NuExtract3 contract)
- Native image upload (no PDF rasterization)
- **Repody VLM** — NuExtract3-GGUF via external **llama-server** (OpenAI-compatible API)
- Structured JSON extraction with NuExtract template types (number, date, verbatim-string, lists, object-arrays, enums, currency, IBAN, etc.)
- Optional markdown extraction mode when no schema fields
- Multi-page PDFs: up to **6 pages** per request
- Extraction result caching in Redis (content + schema fingerprint)
- Processing paths: `document_model` (VLM) vs logic-only (no file)

### Audit execution

- Runs: test runs from builder, production runs via API
- Async processing: Taskiq + Redis Streams
- Two worker pools: **extract** (VLM/GPU bound) and **fast** (logic-only)
- Dispatch outbox in Postgres with replay on transient failures
- Run progress via SSE + Redis pub/sub
- Stale run maintenance and queued-run timeouts
- Admission control: queue depth caps, 503 + `Retry-After`

### Review and reporting

- Audit list and run detail (fields, rule results, violations)
- Dashboard: KPIs, workflow fleet, recent audits, charts
- Audit export routes
- Document markdown preview in workflow builder

### Platform admin

- IAM: users, teams, permissions matrix (Keycloak + Casbin)
- Settings: model runtime, diagnostics, operator benchmarks
- Operator console: benchmark jobs, platform health (`AUDIT_OPERATOR_ACTIONS_ENABLED`)
- Model catalog: document models, live probes, runtime fields panel
- Platform diagnostics: inference, storage, Redis health

### Frontend UX

- **next-intl** localization, **next-themes** dark/light mode
- Command palette, responsive app shell, mobile nav
- **TanStack React Query** for client data fetching

---

## 2. Architecture

### Request lifecycle

```
Browser → Next.js (repody-web)
       → Keycloak OIDC (Auth.js)
       → FastAPI /v1 (repody-api)
       → Postgres (state) + Redis (queue, cache, SSE, rate limits)
       → MinIO/S3 (documents)
       → Taskiq workers → external llama-server (NuExtract3 VLM)
```

See [CONTEXT.md](../CONTEXT.md) for the full sequence diagram and bounded contexts.

### Backend layers

```
backend/src/audit_workbench/
├── api/           HTTP routers → delegate to services
├── services/      Business logic (runs, workflows, admission, dispatch)
├── extraction/    Document pipeline, NuExtract contract, Repody VLM client
├── inference/     OpenAI-compat clients (VLM, validation LLM)
├── rules/         Logic + LLM evaluators
├── taskiq/        Worker entrypoint + async tasks
├── db/            SQLAlchemy models + Alembic
├── schemas/       Pydantic DTOs (camelCase JSON)
├── storage/       Local filesystem + S3/MinIO
├── auth/          OIDC, Casbin RBAC, API keys
├── catalog/       Document model registry and probes
└── observability/ structlog, OTEL, Bugsink, middleware
```

### Frontend layers

- **app/** — Next.js App Router pages (dashboard, workflows, audits, users, settings, login)
- **components/** — feature UI (workflow builder, audit report, dashboard, IAM)
- **lib/** — API client (`openapi-fetch` + generated types), auth, hooks
- **proxy.ts** — OIDC gate; injects session Bearer into `/api/v1/*`

### Architecture decisions (ADRs)

| ADR | Topic | Doc |
|-----|--------|-----|
| 001 | Taskiq + Redis Streams for async runs; dispatch outbox | [adr/001-taskiq-async-runs.md](./adr/001-taskiq-async-runs.md) |
| 002 | External VLM; catalog registry; separate validation LLM | [adr/002-repody-vlm-dual-inference-runtimes.md](./adr/002-repody-vlm-dual-inference-runtimes.md) |
| 003 | Modular Helm: control / workers / data / auth | [adr/003-modular-platform-modules.md](./adr/003-modular-platform-modules.md) |
| 004 | Cloud Kubernetes packaging | [adr/004-cloud-kubernetes-packaging.md](./adr/004-cloud-kubernetes-packaging.md) |
| 005 | Inference always external in K8s | [adr/005-kubernetes-only-external-inference.md](./adr/005-kubernetes-only-external-inference.md) |

---

## 3. Security

### Authentication

| Layer | Technology | Notes |
|-------|------------|-------|
| Browser | Auth.js v5 + Keycloak OIDC | JWT session, refresh, realm roles |
| API | PyJWT + JWKS | Keycloak token validation; issuer aliases |
| Dev bypass | `AUDIT_OIDC_ENABLED=false` | Local dev principal with admin role |
| Production | Settings validator | OIDC required when `AUDIT_DEPLOYMENT_ENVIRONMENT=production` |

### Authorization (RBAC)

- **Casbin** — `rbac_model.conf` + `rbac_policy.csv`
- **Roles:** `platform_admin`, `admin`, `operator`, `viewer`
- **Resources:** workflow, run, audit, upload, metrics, rules, models, operator, diagnostics, settings, users
- **Dual auth on runs:** admin JWT or workflow API key (SHA-256 hash, timing-safe compare)

### Input and upload security

- Upload size limits (`AUDIT_MAX_UPLOAD_BYTES`, default 25 MB)
- MIME allowlist + `filetype` sniffing
- Filename sanitization
- Pydantic validation on all API DTOs
- Workflow validation before deploy

### Rate limiting and admission

- Global HTTP: 300 req/min per IP (`limits` + Redis)
- Per-workflow and per-client run creation limits
- `AUDIT_RATE_LIMIT_FAIL_CLOSED` — reject when Redis unavailable (production)
- Queue depth caps — 503 when overloaded

### Secrets (production)

- Never inline in Helm values — `secrets.existingSecret: repody-runtime-secrets`
- External Secrets Operator + Vault — see [deploy/SECRETS.md](./deploy/SECRETS.md)
- Required keys: `AUDIT_DATABASE_URL`, `AUDIT_REDIS_URL`, MinIO keys, `AUDIT_LLAMACPP_API_KEY`, Keycloak secrets, `BUGSINK_DSN`

### Container and network hardening (Kubernetes)

- Pod Security restricted compatibility
- NetworkPolicy enabled
- Non-root containers
- PDB + HPA on API, web, workers
- Ingress TLS / OpenShift route termination
- Enterprise overlay fails on `latest` tags and inline secrets

### Log security

- Sensitive field redaction in structlog (password, token, api_key, authorization, etc.)
- Bugsink: `send_default_pii=false`, no session tracking

### CI security scanning

- pnpm audit, pip-audit
- Trivy (filesystem, config, secrets, images)
- Grype + Syft SBOM
- `pnpm security:scan`, `pnpm enterprise:secrets`

---

## 4. Performance and reliability

### Async and concurrency

- FastAPI + async SQLAlchemy (`asyncpg`)
- Taskiq async workers with configurable slots per pool
- S3 operations via `asyncio.to_thread()`
- Parallel document extraction in multi-document runs

### Connection pools

| Pool | Settings |
|------|----------|
| Postgres | `AUDIT_DB_POOL_SIZE=5`, `MAX_OVERFLOW=10`, `pool_pre_ping` |
| Redis | `AUDIT_REDIS_MAX_CONNECTIONS=20` (cache, SSE, rate limits, Taskiq) |

### Caching

- Extraction results: Redis, TTL 24h, schema + content fingerprint
- Module-level singletons: settings, storage, broker, authorizer (`@lru_cache`)
- JWKS warmed at API startup

### Extraction pipeline

- Official NuExtract contract in code (`nuextract_contract.py`) — not env-tunable quality knobs
- Repody VLM warmup on worker/API startup (optional)
- GPU cold-start timing metadata
- Progress batching: `AUDIT_PROGRESS_COMMIT_INTERVAL_MS` (default 400 ms)
- llama-server vision token and Vulkan stability settings — see [deploy/llamacpp/README.md](../deploy/llamacpp/README.md)

### Timeouts (aligned)

| Setting | Default |
|---------|---------|
| Worker task | 3 min hard cap |
| VLM request | 180 s |
| Stale run | 5 min |
| Queued stale | 60 min |

### Dispatch durability

- Postgres outbox (`RunDispatchOutbox`) before Taskiq enqueue
- Replay on transient failures; max `AUDIT_DISPATCH_MAX_ATTEMPTS` (8)
- Advisory locks for run claiming

---

## 5. Production deployment

### Targets

| Environment | Method |
|-------------|--------|
| Local dev | Docker Compose + host-run API/UI + optional observability profile |
| Kubernetes | Helm: `repody`, `repody-data`, `repody-auth` |
| OpenShift | Routes, CRC lab scripts — [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |
| Release | GHCR images, cosign attest, GitOps promotion — [deploy/RELEASE.md](./deploy/RELEASE.md) |

### Helm modules

| Chart | Deploys |
|-------|---------|
| **repody** | API, web, workers (extract + fast), ingress/Gateway API, migrations Job, HPA, PDB, NetworkPolicy |
| **repody-data** | Postgres, Redis, MinIO (+ bucket init Job) |
| **repody-auth** | Keycloak + realm import + DB init |

**Profiles:** `external` (BYO Postgres/Redis/S3) vs `bundled` (in-cluster data plane). See [PLATFORM.md](./PLATFORM.md).

### Supply chain

- Pinned images: [VERSIONS.md](./VERSIONS.md), `deploy/pinned-images.env`
- SBOM (Syft), signing (cosign), promotion gates
- Pre-deploy: `pnpm deploy:check`, `pnpm prod:readiness`, `pnpm client:check`

### Production defaults

- `config.logJson: true`
- `observability.otelEnabled` + client-provided OTLP endpoint
- `observability.bugsinkDsn` via runtime secret
- Inference **always external** (never in app chart)

---

## 6. Observability

| Component | Role | Local URL |
|-----------|------|-----------|
| **structlog** | JSON logs, OTEL trace fields, redaction | stdout + `.logs/repody-api.log` |
| **Promtail** | Ship Docker + host API logs → Loki | — |
| **Loki** | Log aggregation | http://localhost:3100 |
| **Grafana** | Explore logs and traces | http://localhost:3030 |
| **Tempo** | Trace storage | http://localhost:3200 |
| **OTEL Collector** | OTLP → Tempo | http://localhost:4318 |
| **Bugsink** | Exception tracking (Sentry-compatible) | http://localhost:8090 |

**Important:** Grafana/Loki capture **log lines** (including `level=error`). **Unhandled exceptions** go to **Bugsink**, not Grafana dashboards.

- Local setup: [OBSERVABILITY.md](./OBSERVABILITY.md)
- Kubernetes: [deploy/OBSERVABILITY.md](./deploy/OBSERVABILITY.md), [deploy/PROD-OBSERVABILITY.md](./deploy/PROD-OBSERVABILITY.md)
- Bugsink: [BUGSINK.md](./BUGSINK.md)

**Host dev API:** install OTEL extra (`uv sync --extra otel`); `pnpm dev:api` passes `--extra otel` automatically.

---

## 7. Inference and document AI

| Item | Detail |
|------|--------|
| Model | NuExtract3-GGUF (Q4_K_M default) |
| Runtime | llama-server — OpenAI `/v1/chat/completions` |
| Vision | mmproj BF16, `--jinja`, `enable_thinking=false`, `temperature=0.2` |
| PDF | PyMuPDF @ 170 DPI PNG |
| Vision tokens | 1024 min/max (Qwen-VL floor + fixed budget) |
| Validation LLM | Separate text model via `instructor` |
| Catalog ID | `repody:vlm` |
| Local scripts | `pnpm llamacpp:serve\|restart\|verify\|warmup` |

Full contract: [REPODY-VLM.md](./REPODY-VLM.md).

---

## 8. Backend libraries

**Python:** ≥3.12 · **Build:** hatchling · **Package manager:** uv

### Core

`fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `python-multipart`, `sse-starlette`, `asgi-correlation-id`

### Data

`sqlalchemy[asyncio]`, `asyncpg`, `alembic`

### Queue and cache

`taskiq`, `taskiq-redis`, `redis`, `limits[async-redis]`

### AI and documents

`instructor`, `openai`, `pillow`, `pymupdf`

### Rules

`simpleeval`

### Auth

`pyjwt[crypto]`, `cryptography`, `casbin`

### Storage and HTTP

`boto3`, `httpx`, `filetype`

### Observability

`structlog`, `sentry-sdk[fastapi]`

### Optional `[otel]`

`opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, instrumentations (FastAPI, httpx, SQLAlchemy, logging)

### Dev `[dev]`

`ruff`, `pyright`, `pytest`, `pytest-asyncio`, `respx`

---

## 9. Frontend libraries

**Node:** ≥24 · **Package manager:** pnpm 11.7

### Core

`next@16`, `react@19`, `typescript@6`

### Auth and i18n

`next-auth@5`, `next-intl@4`

### Data and state

`@tanstack/react-query`, `openapi-fetch`, `@microsoft/fetch-event-source`

### UI

Radix UI, Tailwind CSS 4, `class-variance-authority`, `lucide-react`, `sonner`, `recharts`, `react-markdown`, `next-themes`

### Errors

`@sentry/nextjs` (Bugsink-compatible DSN)

### E2E

`@playwright/test`

---

## 10. Infrastructure and tooling

### Local dev commands

| Command | Purpose |
|---------|---------|
| `pnpm dev:all` | Compose + API + UI + observability |
| `pnpm dev:stack` | Postgres, Redis, MinIO, Keycloak |
| `pnpm dev:api` / `dev:app` | Foreground API or UI |
| `pnpm dev:worker:extract` / `:fast` | Compose workers |
| `pnpm dev:observability` | Grafana, Loki, Tempo, Bugsink, OTEL |
| `pnpm llamacpp:*` | NuExtract llama-server lifecycle |

See [COMMANDS.md](./COMMANDS.md) and [deploy/LOCAL.md](./deploy/LOCAL.md).

### Docker Compose profiles

| Profile | Services |
|---------|----------|
| (default) | postgres, redis, minio, keycloak |
| **workers** | worker-extract, worker-fast |
| **observability** | grafana, loki, tempo, otel-collector, promtail, bugsink |

### CI/CD (GitHub Actions)

| Workflow | Purpose |
|----------|---------|
| `ci.yml` | pytest, lint, typecheck, build, OpenAPI drift, k8s-smoke |
| `security.yml` | Audit, Trivy, Grype, SBOM |
| `images-ghcr.yml` | Build, push, sign images |
| `release-promote.yml` | Signature verification |
| `e2e.yml` | Optional live-stack pytest |

### Quality gates

- Ruff + Pyright (backend)
- ESLint + TypeScript (frontend)
- `pnpm architecture:check` — layer boundaries
- `pnpm review:check` — review checklist
- `pnpm doctor` — environment validation

---

## 11. Testing

| Layer | Tool | Notes |
|-------|------|-------|
| Unit/integration | pytest + pytest-asyncio | 96+ test files |
| Live API | `@pytest.mark.live` | Requires running API + inference |
| Slow extraction | `@pytest.mark.slow` | Full PDF pipeline |
| Playwright E2E | 11 specs in `e2e/tests/` | Auth, smoke, builder, upload, benchmarks |
| CI smoke | `pnpm test:e2e:smoke` | Platform health in CI |
| Security | Trivy, Grype, pip-audit | CI + local |

See [E2E.md](./E2E.md), [BENCHMARKING.md](./BENCHMARKING.md).

---

## 12. API surface

~37 endpoints under `/v1`: health, workflows, runs, audits, uploads, metrics, dashboard, rules library, platform, operator, IAM.

Full inventory: [BACKEND.md](./BACKEND.md).

OpenAPI → `lib/openapi.json` → TypeScript codegen (`pnpm codegen:api`).

---

## 13. Database

**ORM models:** Workflow, Document, SchemaField, WorkflowRule, RuleTemplate, Run, RunDocument, ExtractedField, RuleResult, RunDispatchOutbox, UploadIntent

**Migrations:** Alembic in `backend/alembic/versions/`

**Redis uses:** Taskiq broker, extraction cache, SSE pub/sub, rate limiting, operator job hydration

---

## 14. App pages (Next.js)

| Route | Feature |
|-------|---------|
| `/dashboard` | KPIs, workflow fleet, charts |
| `/workflows`, `/workflows/new`, `/workflows/[id]/edit` | Workflow list and builder |
| `/audits`, `/audits/[id]` | Audit list and run report |
| `/users` | IAM |
| `/settings` | Platform settings |
| `/login`, `/unauthorized` | Auth |

---

## 15. Best practices summary

| Area | Practice |
|------|----------|
| Architecture | Clean layering, ADRs, bounded contexts, outbox pattern, anti-corruption layers |
| Security | OIDC in prod, Casbin RBAC, fail-closed rate limits, secret externalization, CI scanning |
| Observability | Structured JSON logs, OTEL traces, trace↔log correlation, Bugsink for exceptions |
| Performance | Async I/O, worker pools, Redis caching, connection pools, admission control |
| Reliability | Dispatch outbox, stale run reap, advisory locks, health probes, PDB/HPA |
| Supply chain | Pinned images, SBOM, cosign, promotion gates |
| Testing | Layered pyramid, live markers, Playwright smoke in CI, ground-truth fixtures |
| API contract | OpenAPI → TypeScript codegen (no drift) |
| Inference | Official NuExtract contract in code, external llama-server only |

---

## Related docs

| Topic | Doc |
|-------|-----|
| Commands | [COMMANDS.md](./COMMANDS.md) |
| Backend API | [BACKEND.md](./BACKEND.md) |
| Helm modules | [PLATFORM.md](./PLATFORM.md) |
| VLM contract | [REPODY-VLM.md](./REPODY-VLM.md) |
| Client deploy | [deploy/CLIENT.md](./deploy/CLIENT.md) |
| Secrets | [deploy/SECRETS.md](./deploy/SECRETS.md) |
| ADRs | [adr/README.md](./adr/README.md) |
