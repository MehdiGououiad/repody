# Repody — architecture context

Single-page map for tech leads and new contributors. Operational how-tos live in [README.md](./README.md), [DEV.md](./DEV.md), and [DEPLOY.md](./DEPLOY.md). Recorded decisions live in [docs/adr/](./docs/adr/).

## Names (read once)

| Name | Where | Meaning |
|------|--------|---------|
| **Repody** | Product / UI copy | What users see |
| **agentcontrol** | Repo folder, npm package, Docker Compose project | Monorepo root |
| **audit-workbench** | `backend/pyproject.toml` distribution name | Python package publish name |
| **audit_workbench** | `backend/src/audit_workbench/` | Python import path |

Model tags like `agentcontrol/repody-vlm:…` are Docker Model Runner image names (upstream GGUF weights), not a fourth product name.

## Domain glossary

| Term | Meaning |
|------|---------|
| **Workflow** | Configured audit template: documents, field schema, validation rules |
| **Run** | One execution of a workflow against uploaded files (test or production) |
| **Document model** | Vision-language model that maps document images → structured JSON fields (Repody VLM today) |
| **Processing path** | How a document is read (`document_model` = direct image-to-schema) |
| **Logic rule** | Deterministic check via `simpleeval` on extracted fields |
| **LLM rule** | Natural-language rule evaluated by a small text model (separate from Repody VLM) |
| **Worker pool `ocr`** | Hatchet worker that runs document-model extraction (GPU/CPU bound) |
| **Worker pool `fast`** | Hatchet worker for logic-only / no-file runs |

Historical note: API paths and settings still use **“OCR”** in places (`/v1/ocr/models`, `AUDIT_DEFAULT_OCR_MODEL`). That means **document model catalog**, not a separate OCR engine stack.

## Request lifecycle

```mermaid
sequenceDiagram
  participant UI as Next.js UI
  participant API as FastAPI /v1
  participant Store as MinIO / local storage
  participant Q as Hatchet
  participant W as Worker (ocr|fast)
  participant Inf as Inference (DMR or vLLM)

  UI->>API: POST presign / confirm upload
  API->>Store: storage key
  UI->>API: POST /workflows/{id}/runs
  API->>Q: dispatch audit-run workflow
  Q->>W: execute run task
  W->>Store: fetch PDF/image
  W->>Inf: Repody VLM chat completion (document model)
  Inf-->>W: structured JSON fields
  W->>W: validate rules (logic + optional LLM)
  W->>API: persist Run / RuleResults
  UI->>API: GET /runs/{id} (poll / SSE)
```

**Inline dev mode:** when `AUDIT_RUN_JOBS_INLINE=true`, the API runs `process_run` in-process instead of Hatchet (no worker container required).

## Backend layers

```
backend/src/audit_workbench/
├── api/           HTTP routers → mostly delegate to services
├── services/      Business logic (runs, workflows, audits, maintenance)
├── extraction/    Document pipeline, model catalog, Repody VLM client
├── inference/     OpenAI-compat clients (Docker Model Runner, vLLM, structured LLM)
├── rules/         Logic + LLM evaluators
├── hatchet/       Worker entrypoint + workflow definitions
├── db/            SQLAlchemy models + Alembic
├── schemas/       Pydantic DTOs (CamelModel → JSON camelCase)
└── storage/       Local filesystem + S3/MinIO
```

**Intentional coupling:** `api/diagnostics.py` and `api/ocr.py` call extraction/inference directly for operator visibility. Everything else on the hot path goes through services.

## Three registries (do not merge)

| Module | Selects | Example ids |
|--------|---------|-------------|
| `extraction/registry.py` | **Extractor implementation** | `stub`, `pipeline` (`AUDIT_EXTRACTOR`) |
| `extraction/model_registry.py` | **Document model catalog** | `repody:vlm` (legacy `repody:vlm`) |
| `services/document_model_catalog.py` | **Catalog + live runtime probes** | used by `/ocr/models`, diagnostics, healthz |

Flow: `get_extractor()` → `PipelineExtractor` → `parse_document_model()` → `extract_with_repody_vlm()` (legacy name) on the runtime chosen by `AUDIT_INFERENCE_MODE`.

## Inference runtimes

| `AUDIT_INFERENCE_MODE` | Deploy | Document extraction |
|------------------------|--------|---------------------|
| `docker_model_runner` | `pnpm docker:deploy` | Repody VLM GGUF via Docker Model Runner (CPU) |
| `vllm` | `pnpm docker:deploy:gpu` | Repody VLM via vLLM (GPU) |

LLM **rule validation** uses a separate small text model on Docker Model Runner when `AUDIT_LLM_VALIDATION_ENABLED=true`. It never shares the document-model runtime.

**Intentional asymmetry:** `AUDIT_INFERENCE_MODE=vllm` switches **document extraction** to vLLM only. LLM rule validation always uses `get_inference_client()` → Docker Model Runner (or stub). Do not point validation at vLLM unless you add a dedicated `AUDIT_VALIDATION_RUNTIME` setting and record that in an ADR.

Add future document models in `extraction/model_registry.py` (`_registered_models()`).

## Frontend layout

Next.js 16 App Router at repo root (not under `frontend/`):

- `app/` — routes (thin pages)
- `components/` — domain UI (`workflow/`, `audit/`, `dashboard/`)
- `lib/api/` — typed clients; RSC uses `serverApiGet`, client islands use `/api/*` rewrite to backend `/v1/*`

## Platform modules (deploy)

Runtime is split into **modules** (`infra`, `control`, `workers`, `edge`, `obs`, `traces`, `errors`) composed via stack presets. See [docs/PLATFORM.md](./docs/PLATFORM.md) and [ADR 003](./docs/adr/003-modular-platform-modules.md).

| Term | Meaning |
|------|---------|
| **Platform module** | Independently deployable Compose service group (microservice seam) |
| **Stack preset** | Base overlay chain (`dev`, `dev-warm`, `prod`, `prod-scale`, `gpu`) |
| **Worker plane** | Horizontally scaled Hatchet workers (`worker`, `worker-fast`) |

## Compose file chain

Legacy file chains still apply; prefer **`pnpm platform:*`** or module-aware dev flags:

| Goal | Command |
|------|---------|
| Dev + warmup + Loki + GlitchTip | `pnpm dev:warmup -- --logs --glitchtip` |
| Prod scale + addons | `pnpm platform:up -- --stack=prod-scale --with=obs,errors` |
| Scale OCR workers | `pnpm platform:scale -- --stack=prod-scale --worker=3` |

| Goal | Files |
|------|-------|
| Dev (fast) | `compose.yaml` + `compose.cpu.yaml` + `compose.dev.yaml` |
| Prod CPU | `compose.yaml` + `compose.cpu.yaml` + `compose.prod.yaml` |
| Prod GPU | above + `compose.gpu.yaml` |
| CI Playwright smoke | `compose.yaml` + `compose.e2e.yaml` |

Module manifest: [deploy/platform-modules.mjs](./deploy/platform-modules.mjs). Legacy: [scripts/docker.mjs](./scripts/docker.mjs).

## Non-product paths

These directories are agent/tooling assets, not runtime dependencies:

- `.agents/skills/` — Cursor agent skills
- `src/ui-ux-pro-max/` — design reference data for UI skills
- `benchmark-reports/` — local benchmark output

## Tests

| Layer | Command | CI |
|-------|---------|-----|
| Backend unit/integration | `pnpm test:api` | `.github/workflows/ci.yml` |
| Playwright smoke | `pnpm test:e2e:smoke` | `.github/workflows/e2e.yml` (nightly + manual) |
| Full platform | `pnpm test:platform` | Manual / nightly (heavier) |

## Further reading

- [docs/adr/001-hatchet-async-runs.md](./docs/adr/001-hatchet-async-runs.md)
- [docs/adr/002-repody-vlm-dual-inference-runtimes.md](./docs/adr/002-repody-vlm-dual-inference-runtimes.md)
- [docs/BACKEND_STEPS.md](./docs/BACKEND_STEPS.md) — milestone history
- [docs/E2E.md](./docs/E2E.md) — full stack test layers
