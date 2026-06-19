# Repody VLM on CPU (Docker Model Runner)

For GPU (vLLM), see [REPODY-VLM.md](./REPODY-VLM.md) and [DEPLOY.md](../DEPLOY.md#gpu-stack-repody-vlm-via-vllm).

The default CPU path extracts structured fields with **Repody VLM** served by **Docker Model Runner**
(llama.cpp).

## Default configuration

| Variable | Default | Role |
|----------|---------|------|
| `AUDIT_REPODY_VLM_MODEL` | `repody/repody-vlm:q4_k_m-16k` | GGUF model tag in Model Runner |
| `AUDIT_DEFAULT_OCR_MODEL` | `repody:vlm` | Workflow catalog id |
| `AUDIT_DOCKER_MODEL_RUNNER_BASE_URL` | `http://model-runner.docker.internal/engines/llama.cpp/v1` | OpenAI-compatible endpoint |
| `AUDIT_REPODY_VLM_PDF_DPI` | `170` | PDF render DPI, matching the NuExtract PDF example |
| `AUDIT_REPODY_VLM_MAX_EDGE_PX` | unset | Optional VLM downscale cap; unset preserves rendered page size |
| `AUDIT_REPODY_VLM_JPEG_QUALITY` | `95` | Fallback JPEG quality for non-PDF/non-image inputs |
| `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` | `6` | Max pages sent in one extraction call |
| `AUDIT_REPODY_VLM_WARMUP_ON_START` | `true` (OCR worker) | Load VLM weights on worker boot |
| `AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT` | `true` | Platform switch: allow per-document markdown preview |
| `AUDIT_REPODY_VLM_MARKDOWN_MAX_TOKENS` | `8192` | Token budget for the markdown pass |
| `AUDIT_REPODY_VLM_ENABLE_THINKING` | `false` | NuExtract `enable_thinking` (temp 0.6 extract / 1.0 markdown; raises min tokens) |

## Document markdown

Repody VLM uses NuExtract's `mode: "markdown"` pass when a workflow document enables **Document markdown preview** (workflow builder). Otherwise only structured JSON is returned and shown in the UI. Disable markdown platform-wide with `AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT=false`.

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
# or: docker compose -f deploy/compose/base.yaml -f deploy/compose/cpu.yaml -f deploy/compose/dev.yaml logs --tail=300 --timestamps worker api
```

Look for:

- `ocr_worker_warmup_done` — OCR worker finished startup warmup (summary)
- `repody_vlm_warmup_done` — Repody VLM loaded in Model Runner
- `repody_vlm_done` — extraction latency, field count, and markdown char count
- `document_model_extracted` — registry dispatch

## Multi-page PDFs

Repody VLM follows the NuExtract image path: raster image uploads are sent in their original
encoding, while PDFs are rendered to PNG pages at `AUDIT_REPODY_VLM_PDF_DPI` before inference.
It sends up to `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` pages in one call
(capped by `AUDIT_OCR_MAX_PAGES`). Extra rendered pages are dropped with a
`repody_vlm_pages_capped` log warning. Prefer short documents or raise the cap only after
checking Model Runner context limits.

## Adding another document model

Register the model in `backend/src/audit_workbench/extraction/model_registry.py` and
implement its handler in `extract_with_document_model()`.
