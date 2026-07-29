# GLM-OCR (markdown-only)

Catalog id: `glm:ocr`. Document → text/Markdown via the **official zai-org SDK**
([GlmOcr](https://huggingface.co/zai-org/GLM-OCR) + PP-DocLayoutV3). Region OCR
runs against llama-server (`ggml-org/GLM-OCR-GGUF`). Structured field extraction
stays on **Repody VLM** (`repody:vlm` / NuExtract).

The model card **strongly recommends the official SDK** for document parsing
(layout + parallel recognition) over model-only inference. This platform uses
that SDK path only — local and prod share the same Docker/K8s worker image.

## Official sources

| Role | Link |
|---|---|
| Model card (SDK recommended) | [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) |
| SDK source / config | [github.com/zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR) |
| GGUF for llama.cpp | [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF) |
| Layout model | [PP-DocLayoutV3_safetensors](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_safetensors) |

## Install (local == prod)

Bake the official SDK into the extract worker image (default):

```powershell
pnpm dev:all
# or after code/deps change:
pnpm dev:worker:rebuild
```

Compose and `pnpm images:build` default to `REPODY_BACKEND_EXTRAS=otel,glmocr`.
`torch` / `torchvision` resolve from the **PyTorch CPU index** (`tool.uv.sources`
in `backend/pyproject.toml`) so Linux images do not ship unused CUDA/nvidia
wheels — matches `AUDIT_GLM_OCR_LAYOUT_DEVICE=cpu`.

Host Python only needs the extra for unit tests / scripts:

```powershell
cd backend
uv sync --extra glmocr
```

OCR weights still come from llama-server (`pnpm glmocr:serve` on **:8083**).
Layout runs **inside** the extract worker (`AUDIT_GLM_OCR_LAYOUT_DEVICE=cpu`
recommended when the GPU is busy with llama).

## Env

```env
AUDIT_GLM_OCR_ENABLED=true
AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:8083/v1
AUDIT_GLM_OCR_SERVED_MODEL=GLM-OCR
AUDIT_GLM_OCR_TIMEOUT_SECONDS=180
AUDIT_GLM_OCR_LAYOUT_DEVICE=cpu
AUDIT_GLM_OCR_LAYOUT_MODEL_DIR=PaddlePaddle/PP-DocLayoutV3_safetensors
AUDIT_GLM_OCR_SDK_MAX_WORKERS=4
# AUDIT_GLM_OCR_PDF_MAX_PAGES=  # unset = official unlimited
```

Extract workers use `http://host.docker.internal:8083/v1`.

## Start

```powershell
pnpm glmocr:serve
pnpm glmocr:verify
pnpm glmocr:warmup
pnpm glmocr:stop
```

Or with the full platform: `pnpm dev:all` then `pnpm models:warmup`.

## Contract (official SDK)

Aligned with [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) + package
[`glmocr/config.yaml`](https://github.com/zai-org/GLM-OCR/blob/main/glmocr/config.yaml):

- `GlmOcr(mode="selfhosted")` → PP-DocLayoutV3 regions → OCR with
  `Text Recognition:` / `Table Recognition:` / `Formula Recognition:`
- Sampling: `temperature=0.0`, `top_p=0.00001`, `top_k=1`, `repetition_penalty=1.1`,
  `max_tokens=8192`
- PDF raster: **200 DPI** (SDK `page_loader.pdf_dpi`)
- PDF page cap: official `pdf_max_pages: null` (no silent drop). Optional override:
  `AUDIT_GLM_OCR_PDF_MAX_PAGES`
- Region parallelism: SDK default 32; platform default **4** when llama `-np 1`
  (`AUDIT_GLM_OCR_SDK_MAX_WORKERS`)

## Adapter

- Official SDK: `backend/src/audit_workbench/extraction/glm_ocr_sdk.py`
- Catalog adapter: `backend/src/audit_workbench/extraction/glm_ocr.py`
- Unit tests: `backend/tests/unit/extraction/test_glm_ocr.py`
- Live Gououiad: `backend/tests/live/platform/test_glm_gououiad_markdown.py`
  (`GLM_GOUOUIAD_LIVE=1`)

## Related

- [EXTRACTION.md](./EXTRACTION.md) — modular catalog map (NuExtract / Paddle / GLM)
- [deploy/glmocr/README.md](../deploy/glmocr/README.md)
- [REPODY-VLM.md](./REPODY-VLM.md) — structured NuExtract / llama.cpp
- [PADDLEOCR-V6.md](./PADDLEOCR-V6.md) — PP-OCRv6 markdown OCR
- [COMMANDS.md](./COMMANDS.md)
