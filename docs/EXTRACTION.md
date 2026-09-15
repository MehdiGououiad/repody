# Document models (extraction)

Each catalog id is one **adapter** behind the shared extraction pipeline.
Workers call external servers; the backend does not ship model weights.

| Catalog id | Adapter | Official docs | Local serve | Worker needs |
|---|---|---|---|---|
| `repody:vlm` | `extraction/nuextract.py` | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) | `pnpm llamacpp:serve` **:8081** | OpenAI-compat URL only |
| `paddleocr:qwen` | `extraction/paddleocr_qwen.py` | PP-OCR serving + Qwen text→JSON | `:8868` + `pnpm qwen35:serve` **:8084** | HTTP only |
| `glm:qwen` | `extraction/glm_ocr_qwen.py` | GlmOcr SDK markdown + Qwen text→JSON | `:8083` + `:8084` | **`otel,glmocr`** + Qwen URL |

Markdown-only OCR adapters (`paddleocr:v6`, `glm:ocr`) remain as **internal stages** for the Qwen pipelines — they are **not** workflow catalog options.

## Contents

1. [Official-docs posture](#official-docs-posture)
2. [Automode (`nativePdfAuto`)](#automode-nativepdfauto)
3. [Local == prod packaging](#local-prod-packaging)
4. [NuExtract / `repody:vlm`](#nuextract-repodyvlm)
5. [PP-OCRv6](#pp-ocrv6)
6. [GLM-OCR](#glm-ocr)

---

## Official-docs posture

| Path | Official contract | Notes |
|---|---|---|
| `repody:vlm` | NuExtract template JSON, PDF **170 DPI**, temp **0.2** | Vision token cap may be lower than HF defaults for VRAM |
| `paddleocr:qwen` | OCR official `POST /ocr`; JSON stage is **Repody** UI-schema prompt on Qwen | Shared `qwen_text.py` with `glm:qwen` |
| `glm:qwen` | Official GlmOcr SDK whole-page `Text Recognition:` then Qwen JSON | Set `AUDIT_GLM_OCR_LAYOUT_ENABLED=true` for PP-DocLayoutV3 |
| Qwen stage | OpenAI-compatible `response_format` JSON Schema + UI-schema prompt | Constrained decoding when server supports it; parse fallback remains |

NuExtract structured JSON is stored verbatim in `run_documents.extraction_meta.rawText`; leaf rows in `extracted_fields` are derived for UI/rules only.

---

## Automode (`nativePdfAuto`)

Per-document toggle (workflow UI). Not a catalog id — keep selecting `documentModelId` as the OCR/VLM fallback.

| Step | Behavior |
|---|---|
| Input is not PDF | Skip inspector → selected model |
| PDF + Auto on | [pdf-inspector](https://github.com/firecrawl/pdf-inspector) `process_pdf_bytes` |
| Quality OK | Native markdown → Qwen text→JSON (same as `paddleocr:qwen`) |
| Quality weak | Selected `documentModelId` |

**Accept native** only when all hold: `pdf_type == text_based`, `confidence >= AUDIT_PDF_INSPECTOR_MIN_CONFIDENCE` (default `0.7`), no encoding issues, empty `pages_needing_ocr`, markdown length `>= AUDIT_PDF_INSPECTOR_MIN_CHARS` (default `40`). `mixed` / `scanned` / `image_based` always fall back.

Decision is recorded on `extraction_meta.nativePdf`. Dependency: `pdf-inspector` on the extract worker — missing package soft-fails to the selected model.

---

## Local == prod packaging

| Layer | Local (`pnpm platform`) | Prod (Helm) |
|---|---|---|
| Extract worker | Hub image, or **local `otel,glmocr` build** when `--with-glm` | Backend image with extras you publish |
| Python extras | Hub = `otel` (lean). `--with-glm` → `compose.glmocr.yaml` builds `repody-backend:local-glmocr` | Set `REPODY_BACKEND_EXTRAS=otel,glmocr` when releasing if GLM is required |
| NuExtract / Paddle / GLM GGUF | Host scripts on `:8081` / `:8868` / `:8083` | External services; set Helm `config.*BaseUrl` and enable flags |

```bash
pnpm platform -- --with-paddle --with-glm
```

First `--with-glm` worker build downloads torch/layout wheels. Laptop guide: [LOCAL.md](./LOCAL.md).

---

## NuExtract / `repody:vlm`

Repody does not run inference inside the Kubernetes chart. Document extraction calls an external OpenAI-compatible **llama-server** with **NuExtract3**.

Reference: [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF)

### What you configure

Only wiring and operational limits — extraction behavior follows the official NuExtract contract (`extraction/nuextract.py`, `extraction/render.py`).

```env
AUDIT_INFERENCE_MODE=llamacpp
AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1
AUDIT_LLAMACPP_SERVED_MODEL=nuextract3-q4_k_m
AUDIT_LLAMACPP_API_KEY=

AUDIT_REPODY_VLM_TIMEOUT_SECONDS=180
AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT=false
AUDIT_HEALTHZ_PROBE_INFERENCE=false
AUDIT_GPU_LIVE_PROBE=false
```

| Fixed in code (not configurable) | Value |
|----------------------------------|-------|
| PDF raster | PNG @ **170 DPI** |
| Structured temperature | **0.2** non-thinking · **0.6** thinking · **0** with ICL |
| Markdown temperature | **0** non-thinking · **0.7** thinking |
| Read path | NuExtract vision only |

Thinking mode (`AUDIT_REPODY_VLM_ENABLE_THINKING`, default `false`) and page cap (`AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST`, default: all pages) are configurable.

### Local development

```powershell
winget install llama.cpp   # or brew install llama.cpp on macOS
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
```

Guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md). Align `LLAMACPP_MODEL_ALIAS` with `AUDIT_LLAMACPP_SERVED_MODEL`.

### Kubernetes

```yaml
config:
  inferenceMode: llamacpp
  llamacppBaseUrl: https://your-inference-host/v1
  llamacppServedModel: nuextract3-q4_k_m
  repodyVlmTimeoutSeconds: 180

secrets:
  existingSecret: repody-runtime-secrets
```

Put `AUDIT_LLAMACPP_API_KEY` in the runtime secret when the endpoint requires auth.

### NuExtract payload contract

| Input | Behavior |
|-------|----------|
| PDF | PNG @ 170 DPI; **all pages** by default. Optional cap: `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` |
| Image | Native PNG/JPEG/WebP bytes |
| Other MIME | Rejected — upload PDF or image only |
| Structured call | `chat_template_kwargs.template` (`json.dumps(..., indent=4)`), `instructions`, `enable_thinking`, `temperature=0.2` (or `0.6` thinking; `0` with ICL), no `max_tokens` |
| `instructions` | Workflow document notes + `Field guidance:` list — hints here, not in the template |
| Markdown mode | `chat_template_kwargs.mode: "markdown"`, `temperature=0` (`0.7` when thinking) |
| Source of truth | Model JSON as `extraction.rawText`; leaf `extracted_fields` are UI/rules projection |
| ICL examples | `developer` role pairs from workflow `extractionIclExamples` (text only; local only) |

### Endpoint check

```bash
curl -s "$AUDIT_LLAMACPP_BASE_URL/models"
pnpm llamacpp:verify
```

### Extraction accuracy (NuExtract contract)

Follow the [NuExtract3 guide](https://github.com/numindai/nuextract) — do not hardcode document-specific rules:

| Practice | Why |
|----------|-----|
| Use `verbatim-string` for exact copy | Official type for no reformulation |
| Format/location hints in field **description** | Maps to `instructions` |
| Prefer native image uploads | Avoids extra PDF→PNG |
| Keep llama.cpp `--image-min-tokens` ≥ 1024 | Qwen-VL accuracy floor |
| Import NuExtract JSON templates in the builder | Same constructors as the docs |
| Prefer one **full name** field on ID photos | Split nom/prenom often swaps on holograms |
| Missing fields are `null` | Official empty result |

### Troubleshooting (NuExtract)

| Symptom | Check |
|---------|-------|
| `Repody VLM is unavailable` | Workers reach `$AUDIT_LLAMACPP_BASE_URL/models` |
| 401/403 | `AUDIT_LLAMACPP_API_KEY` |
| Timeout | Raise `AUDIT_WORKER_TASK_TIMEOUT_MINUTES` and matching `AUDIT_REPODY_VLM_TIMEOUT_SECONDS` (≤ worker×60). Compose extract defaults to 10 min / 600s |
| Wrong JSON | llama-server started with `--jinja` |
| Truncated output | Reduce schema size or set page cap |
| Digits wrong / extra zeros | Prefer Q8_0 (or Q6) GGUF at vision 1024; `verbatim-string` + length/location in description |

---

## PP-OCRv6

Catalog id: `paddleocr:v6` (markdown-only internal stage). Structured field extraction stays on **`repody:vlm`** or **`paddleocr:qwen`**.

Follows: [Serving](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html) · [OCR pipeline](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)

Enabled by default (`AUDIT_PADDLEOCR_V6_ENABLED=true`). With `pnpm platform`, PP-OCR starts when you pass **`--with-paddle`**.

### Install + run

```powershell
pnpm platform -- --with-paddle
# or alone:
pnpm paddleocr:v6:serve
```

`paddleocr-v6-serve` **auto-installs** into `backend/.venv` on first serve if deps are missing:

1. [PaddlePaddle 3.2.0 CPU](https://www.paddleocr.ai/latest/en/version3.x/paddlepaddle_installation.html)
2. [`paddleocr`](https://www.paddleocr.ai/latest/en/version3.x/installation.html) (pulls `paddlex`)
3. `paddlex[serving]`

Skip auto-install: `REPODY_PADDLEOCR_SKIP_INSTALL=1`. Pipeline: `deploy/paddleocr-v6/OCR.yaml` (PP-OCRv6_medium, `max_num_input_imgs: null`).

Optional env: `AUDIT_PADDLEOCR_V6_DEVICE`, `AUDIT_PADDLEOCR_V6_USE_HPIP`, `AUDIT_PADDLEOCR_V6_HPI_CONFIG`, orientation/unwarp/textline overrides. High-performance inference is **Linux x86-64 only** upstream.

### Invoke

```powershell
pnpm paddleocr:v6:verify
```

Client body matches official example + `visualize: false`. `fileType`: `0` = PDF, `1` = image. Response: `result.ocrResults[].prunedResult.rec_texts`.

### Env

```env
AUDIT_PADDLEOCR_V6_ENABLED=true
AUDIT_PADDLEOCR_V6_BASE_URL=http://127.0.0.1:8868
AUDIT_PADDLEOCR_V6_TIMEOUT_SECONDS=180
AUDIT_PADDLEOCR_V6_USE_DOC_ORIENTATION_CLASSIFY=true
AUDIT_PADDLEOCR_V6_USE_DOC_UNWARPING=true
AUDIT_PADDLEOCR_V6_USE_TEXTLINE_ORIENTATION=true
```

Extract workers use `http://host.docker.internal:8868`.

### Adapter paths

Config: `deploy/paddleocr-v6/OCR.yaml` · Serve: `deploy/scripts/paddleocr-v6-serve.mjs` · Client: `backend/src/repody/extraction/paddleocr_v6.py` · Notes: [deploy/paddleocr-v6/README.md](../deploy/paddleocr-v6/README.md)

---

## GLM-OCR

Catalog ids:

- `glm:ocr` — Document → Markdown via official [GlmOcr](https://huggingface.co/zai-org/GLM-OCR) SDK. Default: whole-page `Text Recognition:` (no layout). Opt-in PP-DocLayoutV3 with `AUDIT_GLM_OCR_LAYOUT_ENABLED=true`.
- `glm:qwen` — same SDK markdown, then **Qwen3.5 text→JSON** (same second stage as `paddleocr:qwen`).

Enable structured: `AUDIT_GLM_OCR_QWEN_ENABLED=true` (and `pnpm qwen35:serve`). Start with `pnpm platform -- --with-glm`.

### Official sources

| Role | Link |
|---|---|
| Model card | [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) |
| SDK | [github.com/zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR) |
| Official NVIDIA | vLLM / SGLang with BF16 |
| Official local / CPU | [Ollama](https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md) — optional via `pnpm glmocr:ollama:serve` |
| **This repo default** | [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF) via `llama-server` (**F16**) |
| Layout | [PP-DocLayoutV3_safetensors](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_safetensors) |

> Local default is **llama-server** on `:8083` (Vulkan/CPU/CUDA) — community GGUF runtime, not zai-org's documented vLLM/SGLang or Ollama. SDK/API contract remains official. Profile: `deploy/glmocr/config.selfhosted.yaml`. Optional ID-card: `AUDIT_GLM_OCR_ID_CARD_PROFILE=true` → `config.idcard.yaml`.

### Install / env

```powershell
pnpm platform -- --with-glm
# or: pnpm glmocr:serve && pnpm glmocr:verify
# host Python: cd backend && uv sync --extra glmocr
```

```env
AUDIT_GLM_OCR_ENABLED=true
AUDIT_GLM_OCR_QWEN_ENABLED=true
AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:8083/v1
AUDIT_GLM_OCR_SERVED_MODEL=GLM-OCR
AUDIT_GLM_OCR_TIMEOUT_SECONDS=600
AUDIT_GLM_OCR_LAYOUT_ENABLED=false
AUDIT_GLM_OCR_LAYOUT_DEVICE=cpu
AUDIT_GLM_OCR_LAYOUT_MODEL_DIR=PaddlePaddle/PP-DocLayoutV3_safetensors
AUDIT_GLM_OCR_SDK_MAX_WORKERS=1
AUDIT_GLM_OCR_ID_CARD_PROFILE=false
AUDIT_QWEN35_BASE_URL=http://127.0.0.1:8084/v1
AUDIT_QWEN35_SERVED_MODEL=Qwen3.5-4B
```

Warmup opt-in: `GLMOCR_WARMUP=on`. Workers use `http://host.docker.internal:8083/v1`.

Optional Ollama: `pnpm glmocr:ollama:serve` then set base URL `http://127.0.0.1:11434` and model `glm-ocr:latest`.

### Contract (official SDK)

**Model-only (default):** whole-page `Text Recognition:` via SDK Pipeline (no PP-DocLayoutV3).

**Document parsing (opt-in):** `AUDIT_GLM_OCR_LAYOUT_ENABLED=true` → PP-DocLayoutV3 → OCR with Text/Table/Formula Recognition prompts.

Shared: llama-server `api_mode=openai`, sampling `temperature=0.0`, `top_p=0.00001`, `top_k=1`, `repetition_penalty=1.1`, PDF raster **200 DPI**.

Notes: [deploy/glmocr/README.md](../deploy/glmocr/README.md)
