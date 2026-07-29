# Backend inventory

Single reference for `backend/` — APIs, scripts, and source layout. For architecture flow see [CONTEXT.md](../CONTEXT.md).

**Package:** `repody` (`backend/src/repody/`)  
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

### Platform (`api/config.py`) — admin

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

Map: [backend/scripts/README.md](../backend/scripts/README.md).

**Ops** (stable `/app/scripts/` paths): `docker-entrypoint.sh`, `bootstrap_migrations.py`, `db_reset.py`, `export_openapi.py`, `auth_oidc_smoke.py`, `platform_integration_suite.py`, `warmup_repody_vlm.py`, `generate_facture_fixture.py`

**Perf / load** (same folder — image + kubectl copy): `load_test_platform.py`, `profile_platform_scale.py`, `locust_api_load.py`, `benchmark_suite.py`, `benchmark_dev_stress.py`, `benchmark_ui_route.py`, `prod_stress_test.py`

**Research** (`research/`): `cnie_structure_llm_bench.py`, `cnie_text_ie_compare.py` — see also `deploy/scripts/research/`

**Repo-root wrappers**: `scripts/prod-stress.mjs`, `scripts/run-platform-e2e.mjs`, `scripts/wait-for-*.mjs`.

---

## Source layout (`backend/src/repody/`)

### Core

| File | Role |
|------|------|
| `main.py` | FastAPI app, middleware, router wiring |
| `settings/` | `AUDIT_*` Pydantic settings (`fields_*.py` + `model.py`) |
| `benchmarking/` | Benchmark scoring helpers (`ocr`, `suite`, `text`) |
| `runtime/` | Pure contracts, recipe, pools, run status/ids, operator validate/job |
| `agents/` | Domain agents (`idp` live; `fraud` / `computer_use` SKIPPED stubs) |
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
| `config.py` | Config, catalog, diagnostics (`/platform/config`, `/models/catalog`, …) |
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

### `infra/db/` — SQLAlchemy

`base.py` (engine/session), `models/` package (ORM), `seed.py` (demo data)

### `infra/auth/` — OIDC + Casbin RBAC

`dependencies.py`, `jwt_validator.py`, `keycloak_token.py` (password grant), `keycloak_admin.py`, `principal.py`, `casbin_authorizer.py`, `rbac_model.conf`, `rbac_policy.csv`

### `extraction/` — Document → fields

| File | Role |
|------|------|
| `pipeline.py` | `extract_document()` + `get_extract_document()` |
| `register.py` | Side-effect import of catalog adapters |
| `vlm.py` | Local + cloud Repody VLM / NuExtract adapters |
| `render.py` | PDF/image page prep + render policies |
| `nuextract.py` | Template types + official chat payloads |
| `fields.py` | NuExtract JSON → schema leaf fields |
| `warmup.py` | `warmup_repody_vlm` |
| `modes.py` | Read paths + validation modes |
| `schema.py` | Schema field specs |
| `types.py` | Types + `ExtractionResult` |
| `branding.py` | Public model labels |
| `cache.py` | Extraction result cache |
| `paddleocr_v6.py` / `glm_ocr.py` / `glm_ocr_sdk.py` | OCR adapters |

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
| `nuextract_cloud.py` | NuExtract cloud REST (module functions) |
| `base.py` | `ChatFn` / `EnsureAvailableFn` type aliases |

### `rules/` — Validation engine

`runner.py`, `logic_evaluator.py`, `llm_evaluator.py`, `llm_fields.py`, `llm_prompts.py`, `conditions.py`, `rule_syntax.py`, `types.py`

### `app/` — Application use cases

| Area | Files |
|------|-------|
| **Runs** | `app/run/` — enqueue → outbox → processor → handoff (`lifecycle`, `persistence`, `progress`, …) |
| **Agents** | `agents/idp/` (compose + adapters); `agents/fraud/`, `agents/computer_use/` (SKIPPED; [ADR 007](./adr/007-staged-agent-queues-taskiq.md)) |
| **Runtime cores** | `runtime/contracts`, `runtime/recipe.py`, `runtime/pools.py`, `runtime/run/*`, `runtime/operator/` |
| **Workflows** | `app/workflow/` (`service`, `repository`, `deployment`, `validation`, `stats`) |
| **App services** | `health.py`, `metrics.py`, `dashboard.py`, `ops/maintenance.py` |
| **Runs extras** | `run/admission.py`, `run/dispatch_outbox.py` |
| **Operator** | `app/operator/` (`jobs`, `benchmarks`, `requests`, `auth`) — I/O; pure types in `runtime/operator/` |
| **Support** | `mappers.py`, `api_keys.py`, `uploads/` (intents · validation · document_slots) |
| **Infra (I/O)** | `infra/redis/`, `infra/rate_limit.py`, `infra/db/`, `infra/storage/`, `infra/auth/`, `infra/observability/` |
| **Catalog** | `catalog/` (not under app) |
| **Rules field ns** | `rules/field_namespace.py` |

### `taskiq/` — Workers

`broker.py`, `tasks.py`, `worker.py`, `models.py`, `__main__.py`

### `schemas/` — Pydantic DTOs

`workflow.py`, `run.py`, `run_requests.py`, `audit.py`, `health.py`, `metrics.py`, `models_catalog.py`, `platform.py`, `rules_library.py`, `uploads.py`, `model_runtime.py`, `operator_requests.py`, `common.py`

### `infra/storage/` — Object storage

`factory.py`, `local.py` (`build_local_store`), `s3.py` (`build_s3_store`), `mime.py`, `base.py` (`ObjectStore` + `PresignedPut`)

### `infra/observability/`

`bootstrap.py`, `logging.py`, `tracing.py`, `middleware.py`, `bugsink.py`, `context.py`

---

## Tests (`backend/tests/`)

Pyramid layout — details in [TESTING.md](./TESTING.md).

| Layer | Focus |
|-------|-------|
| `unit/` | Pure modules: agents, lifecycle, extraction, rules, runtime recipe |
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
| `app/workflow/service.py` vs `app/workflow/repository.py` | Orchestration vs persistence |
