# Backend build — step by step

This tracks **Phase 2** of the Repody plan. Each step builds on the previous one.

## Status overview

| Step | Milestone | Status |
|------|-----------|--------|
| 1 | Foundation (API, Postgres, seed, read APIs) | Done |
| 2 | Alembic migrations | Done |
| 3 | Object storage (local + MinIO/S3) | Done |
| 4 | Uploads API | Done |
| 5 | Extraction registry (`stub` default) | Done |
| 6 | Rule engine (`simpleeval` + LLM stub) | Done |
| 7 | Hatchet worker + async runs | Done |
| 8 | Multipart runs with files | Done |
| 9 | Real extraction (Repody VLM — Model Runner / vLLM) | Done (CPU + GPU compose) |
| 10 | Hardening (observability, bench, CI E2E) | Done (partial — see CONTEXT.md) |

---

## Step 1 — Foundation (done)

**Goal:** Replace Next.js mocks with a real FastAPI service backed by Postgres.

- `backend/src/audit_workbench/` — API, models, services
- `compose.yaml` — postgres, redis, minio, api, web
- Seed workflow `wf-invoice-audit`, audit `AUD-2023-8902`
- Next.js rewrites `/api/*` → backend `/v1/*`

**Verify**

```bash
docker compose up -d postgres api
pnpm dev
# Open http://localhost:3000/dashboard
```

---

## Step 2 — Alembic migrations (done)

**Goal:** Versioned schema instead of only `create_all`.

```bash
cd backend
set AUDIT_DATABASE_URL=postgresql+asyncpg://audit:audit@localhost:5432/audit_workbench
python -m alembic upgrade head
```

Initial revision: `alembic/versions/*_initial_schema.py`

---

## Step 3 — Object storage (done)

**Goal:** Store uploaded PDFs/images for runs.

| File | Role |
|------|------|
| `storage/base.py` | `ObjectStorage` interface |
| `storage/local.py` | Dev/tests — files under `.data/storage/` |
| `storage/s3.py` | MinIO / AWS S3 via boto3 |
| `storage/factory.py` | `AUDIT_STORAGE_BACKEND=local\|s3` |

Bucket is created on API startup (`init_storage()`).

---

## Step 4 — Uploads API (done)

```http
POST /v1/uploads
Content-Type: multipart/form-data
files: (one or more)
```

Response: `{ uploads: [{ id, storageKey, fileName, mimeType, size }] }`

---

## Step 5 — Extraction registry (done)

| File | Role |
|------|------|
| `extraction/base.py` | `DocumentExtractor` ABC |
| `extraction/stub.py` | Deterministic fake values (default) |
| `extraction/registry.py` | `AUDIT_EXTRACTOR=stub` |

**Document models:** Repody VLM via `extraction/repody_vlm.py` and `extraction/model_registry.py` (`AUDIT_EXTRACTOR=pipeline`).

---

## Step 6 — Rule engine (done)

| File | Role |
|------|------|
| `rules/logic_evaluator.py` | `simpleeval` for logic rules |
| `rules/llm_evaluator.py` | LLM via inference client (stub when disabled) |
| `rules/runner.py` | Dispatches by `rule.kind` |

Dry-run and runs use the same evaluator with extracted field values.

---

## Step 7 — Hatchet worker (done)

| File | Role |
|------|------|
| `hatchet/worker.py` | `python -m audit_workbench.hatchet.worker` |
| `hatchet/workflows/audit_run.py` | `audit-run` workflow → `process_run` |
| `services/run_dispatch.py` | Trigger Hatchet after API commit |
| `services/worker_pool.py` | Route runs to `fast` or `ocr` worker pools |

**Docker with workers**

```bash
docker compose -f compose.yaml -f compose.cpu.yaml up -d postgres redis minio hatchet-lite api worker worker-fast
```

**Local dev (inline, no worker)**

```bash
set AUDIT_RUN_JOBS_INLINE=true
uvicorn audit_workbench.main:app --reload --port 8000
```

---

## Step 8 — Multipart runs (done)

```http
POST /v1/workflows/{id}/runs?mode=test
Content-Type: multipart/form-data
files: invoice.pdf
document_ids: ["doc-invoice"]   # optional JSON array, same order as files
```

Returns `202 { runId, jobId, status }`. Poll `GET /v1/runs/{runId}`.

Legacy sync test (UI today):

```http
POST /v1/workflows/{id}/test-run
```

---

## Step 9 — Real extraction (done)

See [OCR_CPU.md](./OCR_CPU.md) for CPU (Docker Model Runner) and [REPODY-VLM.md](./REPODY-VLM.md) / [DEPLOY.md](../DEPLOY.md#gpu-stack-repody-vlm-via-vllm) for GPU (vLLM).

```powershell
pnpm docker:up          # dev CPU
pnpm docker:deploy      # prod CPU
pnpm docker:deploy:gpu  # prod GPU (vLLM)
```

| File / compose | Role |
|----------------|------|
| `extraction/repody_vlm.py` | Repody VLM image-to-schema extraction |
| `extraction/model_registry.py` | Pluggable document model catalog |
| `compose.cpu.yaml` | Docker Model Runner + Repody VLM CPU tuning |
| `compose.gpu.yaml` | vLLM service + `AUDIT_INFERENCE_MODE=vllm` overlay |

---

## Step 10 — Hardening (done / ongoing)

Delivered:

- Observability stack — [OBSERVABILITY.md](./OBSERVABILITY.md)
- Benchmark scripts — [BENCHMARKING.md](./BENCHMARKING.md)
- Architecture context — [CONTEXT.md](../CONTEXT.md) + [docs/adr/](./adr/)
- Playwright smoke in CI — `.github/workflows/e2e.yml` (nightly + manual; `pnpm test:e2e:smoke` locally)

Still optional / incremental:

- `tenacity` on inference calls
- Dedicated `llm_evaluator` unit tests
- Frontend component tests

---

## Environment reference

See repo `.env.example`. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIT_DATABASE_URL` | postgres local URL | SQLAlchemy async |
| `AUDIT_REDIS_URL` | `redis://localhost:6379/0` | SSE, cache, rate limits |
| `AUDIT_STORAGE_BACKEND` | `local` | `local` or `s3` |
| `AUDIT_RUN_JOBS_INLINE` | `true` | `false` → Hatchet workers |
| `AUDIT_EXTRACTOR` | `pipeline` | Document model extraction (`stub` for tests) |
| `AUDIT_INFERENCE_MODE` | `docker_model_runner` | `docker_model_runner` (CPU) or `vllm` (GPU) |

---

## Tests

```bash
cd backend
python -m pytest tests/ -v -m "not live"
pnpm test:platform   # from repo root — full stack E2E
```
