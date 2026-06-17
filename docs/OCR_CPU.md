# Repody VLM on CPU (Docker Model Runner)

For GPU (vLLM), see [REPODY-VLM.md](./REPODY-VLM.md) and [DEPLOY.md](../DEPLOY.md#gpu-stack-repody-vlm-via-vllm).

The platform extracts structured fields with **Repody VLM** served by **Docker Model Runner**
(llama.cpp). There is no separate OCR stack.

## Default configuration

| Variable | Default | Role |
|----------|---------|------|
| `AUDIT_REPODY_VLM_MODEL` | `repody/repody-vlm:q4_k_m-16k` | GGUF model tag in Model Runner |
| `AUDIT_DEFAULT_OCR_MODEL` | `repody:vlm` | Workflow catalog id |
| `AUDIT_DOCKER_MODEL_RUNNER_BASE_URL` | `http://model-runner.docker.internal/engines/llama.cpp/v1` | OpenAI-compatible endpoint |
| `AUDIT_REPODY_VLM_PDF_DPI` | `120` | PDF render DPI |
| `AUDIT_REPODY_VLM_MAX_EDGE_PX` | `1024` | Longest page edge before inference |
| `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` | `4` | Max pages sent in one extraction call |
| `AUDIT_REPODY_VLM_WARMUP_ON_START` | `true` (OCR worker) | Load VLM weights on worker boot |

## Start the stack

```powershell
pnpm prod
# or production-like:
pnpm compose up --stack=prod --build
```

Pull / prepare Repody VLM (packages upstream GGUF as `repody/repody-vlm:q4_k_m-16k`):

```powershell
pnpm models:pull
```

## Verify

```powershell
curl http://localhost:8000/v1/healthz
curl http://localhost:8000/v1/models/catalog
pnpm test:platform:integration
```

## Logs

```powershell
pnpm compose logs --stack=dev
# or
pnpm compose logs --stack=dev
# or: docker compose -f deploy/compose/base.yaml -f deploy/compose/cpu.yaml -f deploy/compose/dev.yaml logs --tail=300 --timestamps worker api
```

Look for:

- `ocr_worker_warmup_done` — OCR worker finished startup warmup (summary)
- `repody_vlm_warmup_done` — Repody VLM loaded in Model Runner
- `repody_vlm_done` — extraction latency and field count
- `document_model_extracted` — registry dispatch

## Multi-page PDFs

Repody VLM is designed for single-image requests upstream; this platform renders each PDF
page to JPEG and sends up to `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` pages in one call
(capped by `AUDIT_OCR_MAX_PAGES`). Extra rendered pages are dropped with a
`repody_vlm_pages_capped` log warning. Prefer short documents or raise the cap only after
checking Model Runner context limits.

## Adding another document model

Register the model in `backend/src/audit_workbench/extraction/model_registry.py` and
implement its handler in `extract_with_document_model()`.
