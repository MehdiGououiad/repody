# Backend inventory

Single reference for `backend/` — APIs, scripts, and source layout. For architecture flow see [CONTEXT.md](../CONTEXT.md).

**Package:** `audit_workbench` (`backend/src/audit_workbench/`)  
**Entry:** `main.py` → FastAPI app on `/v1/*`

---

## HTTP API (37 endpoints)

All routes mount at `/v1`. Admin routes require OIDC JWT (`require_management_access`). Run routes accept admin JWT or workflow API key.

### Health (`api/health.py`) — public

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz/live` | Liveness (process is answering) |
| `GET` | `/healthz` | Readiness (queue depth, optional inference probe) |

### Workflows (`api/workflows.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/workflows` | List workflows |
| `POST` | `/workflows` | Create workflow |
| `POST` | `/workflows/bulk-delete` | Archive many workflows |
| `GET` | `/workflows/{id}` | Get workflow |
| `PUT` | `/workflows/{id}` | Update workflow |
| `DELETE` | `/workflows/{id}` | Archive workflow |
| `POST` | `/workflows/{id}/deploy` | Deploy (issue API key) |
| `POST` | `/workflows/{id}/dry-run` | Validate without persisting |

### Runs (`api/runs.py`) — mixed auth

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/runs/{id}/status` | Lightweight poll (status + progress) |
| `GET` | `/runs/{id}` | Full poll (`?full=false` ≡ status) or audit when done |
| `GET` | `/runs/{id}/events` | SSE progress stream |
| `POST` | `/workflows/{id}/runs` | Create run (multipart upload) |
| `POST` | `/workflows/{id}/runs/json` | Create run (presigned files + JSON body) |

### Audits (`api/audits.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/audits` | List completed runs (`limit`, `offset`, `total`) |
| `GET` | `/audits/{id}` | Full audit report (`id` = run id) |

### Metrics (`api/metrics.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/metrics` | Platform usage metrics |

### Dashboard (`api/dashboard.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/dashboard` | Bundled dashboard snapshot (metrics + recent audits + workflow summaries + queue) |

The web UI loads the dashboard from `/dashboard` (SSR + live refresh). `/metrics`, `/audits`, and `/workflows` remain available for direct API use.

### Rules (`api/rules_library.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/rules/library` | Rule template library |

### Uploads (`api/uploads.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/uploads/capabilities` | MIME limits, presign support |
| `POST` | `/uploads/presign` | Presigned PUT URLs |
| `POST` | `/uploads/confirm` | Confirm presigned uploads |
| `POST` | `/uploads` | Direct multipart upload |

### Platform (`api/platform.py`) — admin

Consolidated config, catalog, and diagnostics.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/platform/config` | Safe `AUDIT_*` snapshot for settings UI |
| `GET` | `/models/catalog` | Document models + paths + validation modes (live probes) |
| `GET` | `/diagnostics/document-model` | Document model reachability (`?run_infer=true` for probe) |

### Operator (`api/operator.py`) — admin, gated by `AUDIT_OPERATOR_ACTIONS_ENABLED`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/operator/status` | Operator panel state |
| `GET` | `/operator/jobs` | List background jobs |
| `GET` | `/operator/jobs/{id}` | Job detail |
| `GET` | `/operator/jobs/{id}/report` | Job HTML/JSON report |
| `GET` | `/operator/jobs/{id}/artifacts/{json\|csv\|html}` | Download artifact |
| `GET` | `/operator/benchmarks/latest` | Latest benchmark report |
| `POST` | `/operator/models/pull` | Returns local runtime install guidance |
| `POST` | `/operator/models/warmup` | Warmup document model |
| `POST` | `/operator/benchmarks` | Start benchmark job |

---

## Scripts (`backend/scripts/`)

| Script | Purpose |
|--------|---------|
| `auth_oidc_smoke.py` | Keycloak + JWT smoke test |
| `benchmark_dev_stress.py` | Dev queue stress (burst + random traffic) |
| `benchmark_suite.py` | Operator API benchmark (`quick` / `models` / `full` profiles) |
| `benchmark_ui_route.py` | Presign + `/runs/json` path helper (used by stress) |
| `prod_stress_test.py` | Production-scale stress (`pnpm stress:prod`) |
| `bootstrap_migrations.py` | Alembic upgrade to head |
| `docker-entrypoint.sh` | Container entry (migrations, exec) |
| `export_openapi.py` | Export OpenAPI to `lib/api/openapi.json` |
| `generate_facture_fixture.py` | Generate `e2e/fixtures/documents/Facture.pdf` |
| `platform_integration_suite.py` | Fresh deploy verification (uses `integration.*`) |
| `warmup_repody_vlm.py` | One-shot Repody VLM warmup |

**Repo-root wrappers** (not in `backend/scripts/`): `scripts/prod-stress.mjs`, `scripts/run-platform-e2e.mjs`, `scripts/wait-for-*.mjs`.

---

## Source layout (`backend/src/audit_workbench/`)

### Core

| File | Role |
|------|------|
| `main.py` | FastAPI app, middleware, router wiring |
| `settings/` | `AUDIT_*` Pydantic settings (`fields_*.py` + `model.py`) |
| `benchmarking.py` | Benchmark scoring + report helpers |
| `integration/` | Shared E2E helpers (`facture`, `fixtures`, `live_stack`, `workflow_flow`) for tests + scripts |

### `api/` — HTTP layer (thin)

| File | Role |
|------|------|
| `deps.py` | DB session dependency |
| `openapi_config.py` | OpenAPI customization |
| `health.py` | Health probes |
| `workflows.py` | Workflow CRUD + deploy |
| `runs.py` | Run create, poll, SSE |
| `runs_enqueue.py` | Run enqueue HTTP helpers |
| `audits.py` | Audit list/detail |
| `metrics.py` | Metrics endpoint |
| `rules_library.py` | Rule templates |
| `uploads.py` | Upload + presign |
| `platform.py` | Config, catalog, diagnostics |
| `operator.py` | Model warmup, benchmarks, job status |

### `catalog/` — Document model catalog

| File | Role |
|------|------|
| `registry.py` | `DocumentModelSpec`, `parse_document_model`, extraction dispatch |
| `adapters.py` | Pluggable extractors (breaks catalog ↔ VLM import cycle) |
| `probes.py` | Runtime availability + generation probes |
| `api.py` | `fetch_models_catalog`, processing paths |
| `runtime_fields.py` | Operator model runtime config assembly |

Import `catalog/registry.py` directly from extraction and API call sites.

### `db/` — SQLAlchemy

`base.py` (engine/session), `models/` package (ORM), `seed.py` (demo data)

### `auth/` — OIDC + Casbin RBAC

`dependencies.py`, `jwt_validator.py`, `keycloak_token.py` (password grant), `keycloak_admin.py`, `principal.py`, `casbin_authorizer.py`, `rbac_model.conf`, `rbac_policy.csv`

### `extraction/` — Document → fields

| File | Role |
|------|------|
| `pipeline.py` | `extract_document()` + `get_extract_document()` |
| `vlm.py` | Local + cloud Repody VLM extract adapters |
| `render.py` | PDF/image page prep + render policies |
| `payloads.py` | VLM prompts + response mapping |
| `warmup.py` | Repody VLM warmup |
| `parse.py` | Parse NuExtract JSON → fields |
| `template_types.py` | Infer NuExtract leaf types |
| `render.py` | Page/image/PDF prep + render policies |
| `payloads.py` | Prompts, ICL messages, response mapping |
| `warmup.py` | `warmup_repody_vlm` + warmup helpers |
| `modes.py` | Read paths + validation modes |
| `schema.py` | Schema field specs |
| `types.py` | Types + `ExtractionResult` |
| `nuextract.py` | NuExtract helpers |
| `branding.py` | Public model labels |
| `cache.py` | Extraction result cache |
| `markdown_normalize.py` | Normalize NuExtract markdown for UI preview |

### `inference/` — LLM clients

| File | Role |
|------|------|
| `factory.py` | `get_chat()` / `get_ensure_available()` |
| `validation_client.py` | `chat_validation` + availability ping |
| `validation_model.py` | Resolve validation model id |
| `openai_compat.py` | OpenAI-compatible HTTP client |
| `runtime.py` | External VLM runtime helpers |
| `structured.py` | JSON-schema structured chat |
| `structured_models.py` | Pydantic LLM output models |
| `availability.py` | Cached LLM availability probes |
| `stub.py` | Stub chat callable |
| `base.py` | `ChatFn` / `EnsureAvailableFn` type aliases |

### `rules/` — Validation engine

`runner.py`, `logic_evaluator.py`, `llm_evaluator.py`, `llm_fields.py`, `llm_prompts.py`, `conditions.py`, `rule_syntax.py`, `types.py`

### `services/` — Business logic

| Area | Files |
|------|-------|
| **Runs** | `enqueue_run` → outbox → `processor` → one `execute_platform_run` stage → optional `handoff` to next agent pool |
| **Run (flat)** | `lifecycle.py`, `commands.py`, `persistence.py`, `events.py`, `handoff.py`, `snapshot.py`, `progress.py`, `helpers.py` |
| **IDP agent** | `agents/idp/` — `contracts.py`, `compose.py`, `run.py`, `adapters/{mapping,extract,validate,persist}.py` |
| **Fraud / CU** | `agents/fraud/`, `agents/computer_use/` (SKIPPED); pools `fraud` / `computer_use` ([ADR 007](./adr/007-staged-agent-queues-taskiq.md)) |
| **Platform cores** | `platform/contracts`, `platform/recipe.py` (staged), `platform/pools.py`, `platform/run/*`, `platform/operator/` |
| **Workflows** | `services/workflow/` (`service`, `repository`, `deployment`, `validation`, `stats`) |
| **Platform** | `platform_health.py`, `catalog/`, `metrics_service.py`, `maintenance.py`, `admission.py`, `rate_limit.py` |
| **Operator** | `services/operator/` (`jobs`, `job_model`, `benchmarks`, `requests`, `reports`, `auth`) |
| **Support** | `mappers.py`, `api_keys.py`, `upload_validation.py`, `document_slots.py`, `field_namespace.py`, `redis_pool.py` |

### `taskiq/` — Workers

`broker.py`, `tasks.py`, `worker.py`, `models.py`, `__main__.py`

### `schemas/` — Pydantic DTOs

`workflow.py`, `run.py`, `run_requests.py`, `audit.py`, `health.py`, `metrics.py`, `models_catalog.py`, `platform.py`, `rules_library.py`, `uploads.py`, `model_runtime.py`, `operator_requests.py`, `common.py`

### `storage/` — Object storage

`factory.py`, `local.py` (`build_local_store`), `s3.py` (`build_s3_store`), `mime.py`, `base.py` (`ObjectStore` + `PresignedPut`)

### `observability/`

`bootstrap.py`, `logging.py`, `tracing.py`, `middleware.py`, `bugsink.py`, `context.py`

---

## Tests (`backend/tests/`)

Pyramid layout — details in [TESTING.md](./TESTING.md).

| Layer | Focus |
|-------|-------|
| `unit/` | Pure modules: agents, lifecycle, extraction, rules, platform recipe |
| `integration/` | ASGI + Postgres / storage (no Taskiq workers) |
| `live/` | Running API (+ workers for run completion); marker `live` |
| `helpers/` · `fixtures/` | Shared fixtures |

| Command | Scope |
|---------|-------|
| `pnpm test:unit` | `backend/tests/unit` |
| `pnpm test:integration` | `backend/tests/integration` |
| `pnpm test:api` | Unit + integration (`not live`) |
| `pnpm test:e2e:smoke` | Playwright smoke |

---

## Intentional overlaps (not bugs)

| Overlap | Why kept |
|---------|----------|
| `GET /runs/{id}/status` vs `GET /runs/{id}?full=false` | Frontend poll uses `/status`; alias documented |
| `GET /audits/{id}` vs `GET /runs/{id}` when done | Admin audit namespace vs run poll |
| `platform/config` vs `models/catalog` | Static config vs live catalog + paths |
| `services/workflow/service.py` vs `services/workflow/repository.py` | Orchestration vs persistence |
