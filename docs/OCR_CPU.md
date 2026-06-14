# Repody VLM on CPU (Docker Model Runner)

For GPU (vLLM), see [REPODY-VLM.md](./REPODY-VLM.md) and [DEPLOY.md](../DEPLOY.md#gpu-stack-repody-vlm-via-vllm).

The platform extracts structured fields with **Repody VLM** served by **Docker Model Runner**
(llama.cpp). There is no separate OCR stack.

## Default configuration

| Variable | Default | Role |
|----------|---------|------|
| `AUDIT_REPODY_VLM_MODEL` | `agentcontrol/repody-vlm:q4_k_m-16k` | GGUF model tag in Model Runner |
| `AUDIT_DEFAULT_OCR_MODEL` | `repody:vlm` | Workflow catalog id |
| `AUDIT_DOCKER_MODEL_RUNNER_BASE_URL` | `http://model-runner.docker.internal/engines/llama.cpp/v1` | OpenAI-compatible endpoint |
| `AUDIT_REPODY_VLM_PDF_DPI` | `120` | PDF render DPI |
| `AUDIT_REPODY_VLM_MAX_EDGE_PX` | `1024` | Longest page edge before inference |
| `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` | `4` | Max pages sent in one extraction call |
| `AUDIT_REPODY_VLM_WARMUP_ON_START` | `true` (OCR worker) | Load weights on worker boot |

## Start the stack

```powershell
pnpm platform:start
# or production-like:
pnpm docker:deploy
```

Pull / prepare Repody VLM (packages upstream GGUF as `agentcontrol/repody-vlm:q4_k_m-16k`):

```powershell
pnpm docker:models:pull
```

## Verify

```powershell
curl http://localhost:8000/v1/healthz
curl http://localhost:8000/v1/ocr/models
pnpm test:platform:integration
```

## Logs

```powershell
pnpm docker:logs:platform
# or
docker compose -f compose.yaml -f compose.cpu.yaml -f compose.dev.yaml logs --tail=300 --timestamps worker api
```

Look for:

- `repody_vlm_warmup_done` — Repody VLM loaded in Model Runner
- `repody_vlm_done` — extraction latency and field count
- `document_model_extracted` — registry dispatch

## Multi-page PDFs

Repody VLM is designed for single-image requests upstream; this platform renders each PDF
page to JPEG and sends up to `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` pages in one call
(capped by `AUDIT_OCR_MAX_PAGES`). Extra rendered pages are dropped with a
`repody_vlm_pages_capped` log warning. Prefer short documents or raise the cap only after
checking Model Runner context limits.

## Optional LLM rule validation

Disabled by default. LLM rules validate **extracted field values** with a dedicated text
model — not Repody VLM.

```powershell
pnpm docker:models:pull:validation
```

```env
AUDIT_LLM_VALIDATION_ENABLED=true
AUDIT_VALIDATION_MODEL=agentcontrol/validation:q4_k_m-4k
```

`AUDIT_STRUCTURED_LLM_ENABLED` is turned on automatically when LLM validation is enabled,
so rule verdicts use Pydantic-validated JSON from Docker Model Runner.

Extraction still uses Repody VLM only.

## Adding another document model

Register the model in `backend/src/audit_workbench/extraction/model_registry.py` and
implement its handler in `extract_with_document_model()`.
