# Backend inventory

Single reference for `backend/` — APIs, scripts, and source layout. For architecture flow see [CONTEXT.md](../CONTEXT.md).

**Package:** `audit_workbench` (`backend/src/audit_workbench/`)  
**Entry:** `main.py` → FastAPI app on `/v1/*`

---

## HTTP API (36 endpoints)

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
| `GET` | `/audits` | List completed runs |
| `GET` | `/audits/{id}` | Full audit report (`id` = run id) |

### Metrics (`api/metrics.py`) — admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/metrics` | Platform usage metrics |

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
| `GET` | `/diagnostics/ocr` | Document model reachability (`?run_infer=true` for probe) |

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
| `benchmark_dev.py` | CLI: `stress` \| `queue` \| `experiments` |
| `benchmark_dev_stress.py` | Stress subcommand implementation |
| `benchmark_dev_queue.py` | Queue depth subcommand |
| `benchmark_dev_experiments.py` | Extraction A/B experiments |
| `benchmark_document_models.py` | Single-file document model benchmark |
| `benchmark_suite.py` | Full API benchmark (`quick` / `models` / `full` profiles) |
| `benchmark_ui_route.py` | Presign + `/runs/json` path benchmark |
| `bootstrap_migrations.py` | Alembic upgrade / baseline stamp |
| `docker-entrypoint.sh` | Container entry (migrations, exec) |
| `export_openapi.py` | Export OpenAPI to `lib/api/openapi.json` |
| `generate_facture_fixture.py` | Generate `e2e/fixtures/documents/Facture.pdf` |
| `platform_integration_suite.py` | Fresh deploy verification (uses `integration.*`) |
| `warmup_repody_vlm.py` | One-shot Repody VLM warmup |

**Repo-root wrappers** (not in `backend/scripts/`): `scripts/benchmark.mjs`, `scripts/run-platform-e2e.mjs`, `scripts/wait-for-*.mjs`.

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
| `pipeline.py` | `PipelineExtractor` + `get_extractor()` |
| `repody_vlm.py` | Repody VLM facade (warmup + extract) |
| `repody_vlm_warmup.py` | Worker startup warmup |
| `repody_vlm_extract.py` | Structured + markdown extraction |
| `document_modes.py` | Read paths + validation modes |
| `field_json.py` | Parse model JSON → field rows |
| `preprocess.py` | Image/PDF prep |
| `pdf_pages.py` | PDF rasterization |
| `document_bundle.py` | Multi-doc bundles |
| `cache.py` | Extraction result cache |
| `base.py` | Types + `ExtractionResult` |
| `stub.py` | Test stub extractor |
| `ocr_markdown.py` | Normalize markdown in raw text |
| `gpu_cold_start.py` | Serverless GPU cold-start hints |
| `extraction_display.py` | Progress UI strings |
| `schema_fields.py` | Empty/sample schema helpers |
| `document_model_branding.py` | Public model labels |

### `inference/` — LLM clients

| File | Role |
|------|------|
| `factory.py` | `get_inference_client()` → validation client |
| `validation_client.py` | Text model for LLM rules |
| `validation_model.py` | Resolve validation model id |
| `openai_compat.py` | OpenAI-compatible HTTP client |
| `runtime.py` | External VLM runtime helpers |
| `structured.py` | JSON-schema structured chat |
| `structured_models.py` | Pydantic LLM output models |
| `availability.py` | Cached LLM availability probes |
| `stub.py` | Test stub |
| `base.py` | Client ABC |

### `rules/` — Validation engine

`runner.py`, `logic_evaluator.py`, `llm_evaluator.py`, `llm_fields.py`, `llm_prompts.py`, `conditions.py`, `rule_syntax.py`, `types.py`

### `services/` — Business logic

| Area | Files |
|------|-------|
| **Runs** | `run_enqueue.py`, `run_enqueue_errors.py`, HTTP mapping in `api/run_enqueue_http.py`, `queue/` (position + progress), `run_service.py`, `run_dispatch.py`, `dispatch_outbox.py`, `run_processor.py`, `run_events.py`, `run_progress.py`, `run_lock.py`, `run_terminal.py`, `run_upload_bindings.py`, `run_pool_classifier.py` |
| **Run phases** | `run/extraction.py`, `run/validation.py`, `run/snapshot.py`, `run/phase_state.py`, `run/helpers.py`, `run/extraction_jobs.py` |
| **Workflows** | `services/workflow/` (`service`, `repository`, `deployment`, `validation`, `stats`) |
| **Platform** | `platform_health.py`, `catalog/`, `metrics_service.py`, `maintenance.py`, `admission.py`, `rate_limit.py` |
| **Operator** | `services/operator/` (`jobs`, `job_model`, `benchmarks`, `requests`, `reports`, `auth`) |
| **Support** | `mappers.py`, `api_keys.py`, `upload_validation.py`, `document_slots.py`, `field_namespace.py`, `redis_pool.py` |

### `taskiq/` — Workers

`broker.py`, `tasks.py`, `worker.py`, `models.py`, `__main__.py`

### `schemas/` — Pydantic DTOs

`workflow.py`, `run.py`, `run_requests.py`, `audit.py`, `health.py`, `metrics.py`, `models_catalog.py`, `platform.py`, `rules_library.py`, `uploads.py`, `model_runtime.py`, `operator_requests.py`, `common.py`

### `storage/` — Object storage

`factory.py`, `local.py`, `s3.py`, `mime.py`, `base.py`

### `observability/`

`bootstrap.py`, `logging.py`, `tracing.py`, `middleware.py`, `bugsink.py`, `context.py`

---

## Tests (`backend/tests/`)

| Area | Focus |
|------|-------|
| `test_api/` | HTTP contracts, operator, uploads |
| `test_auth/` | JWT, Casbin, run-create access |
| `test_e2e/` | Facture workflow live tests (imports `audit_workbench.integration`) |
| `test_extraction/` | Pipeline, PDF, field parsing |
| `test_taskiq/` | Workflow input payload |
| `test_inference/` | Structured LLM, vLLM runtime |
| `test_observability/` | Logging, BugSink |
| `test_platform/` | Live stack, benchmarking |
| `test_rules/` | Logic conditions |
| `test_services/` | Runs, admission, workflows, locks |
| `test_storage/` | Local + S3 presign |

---

## Intentional overlaps (not bugs)

| Overlap | Why kept |
|---------|----------|
| `GET /runs/{id}/status` vs `GET /runs/{id}?full=false` | Frontend poll uses `/status`; alias documented |
| `GET /audits/{id}` vs `GET /runs/{id}` when done | Admin audit namespace vs run poll |
| `platform/config` vs `models/catalog` | Static config vs live catalog + paths |
| `workflow_service` vs `workflow_repository` | Orchestration vs persistence |
