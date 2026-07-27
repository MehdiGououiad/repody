# GLM-OCR (markdown-only)

Catalog id: `glm:ocr`. Document → text/Markdown via llama-server OpenAI `POST /v1/chat/completions`. Structured field extraction stays on **Repody VLM** (`repody:vlm` / NuExtract).

## Official sources

| Role | Link |
|---|---|
| Model card (prompts / tasks) | [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) |
| GGUF for llama.cpp | [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF) (converted from zai-org) |
| llama.cpp OCR blog | [Using OCR models with llama.cpp](https://huggingface.co/blog/ggml-org/using-ocr-models-with-llama-cpp) |

We serve the **GGUF** via `llama-server` (same stack as NuExtract). Prompts follow the **zai-org** model card, not the generic `"OCR"` example in the ggml blog.

**Not implemented (yet):** the full zai SDK + PP-DocLayoutV3 layout pipeline, nor vLLM / SGLang / Ollama as first-class runtimes. This adapter is page-raster → chat OCR.

Enabled in the catalog by default (`AUDIT_GLM_OCR_ENABLED=true`). Started by `pnpm dev:all` on **:8083** (skip with `--no-glmocr`).

## Env

```env
AUDIT_GLM_OCR_ENABLED=true
AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:8083/v1
AUDIT_GLM_OCR_SERVED_MODEL=GLM-OCR
AUDIT_GLM_OCR_TIMEOUT_SECONDS=180
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

Default serve uses `llama-server -hf ggml-org/GLM-OCR-GGUF` on **:8083**. Optional local paths: copy `deploy/glmocr/paths.local.env.example` → `paths.local.env`.

## Contract (zai-org document parsing)

Aligned with [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) + official SDK
[`glmocr/config.yaml`](https://github.com/zai-org/GLM-OCR/blob/main/glmocr/config.yaml)
`page_loader` defaults (not the generic ggml `"OCR"` blog example):

- User content: **image first**, then **`Text Recognition:`**
- Sampling: `temperature=0.0`, `top_p=0.00001`, `top_k=1`, `repeat_penalty=1.1`, `max_tokens=8192`
- PDF raster: **200 DPI** PNG
- No platform longest-edge downscale (model smart-resizes)
- Serve: `llama-server -hf ggml-org/GLM-OCR-GGUF` (Q8_0 default; use `:F16` for max quality)

### Known accuracy gap vs full SDK

Model-only chat (this adapter) does **not** run PP-DocLayoutV3 region cropping from the
official SDK. For single-page ID cards that is usually fine; for dense multi-region
documents the full SDK can score higher.

## Adapter

Shared chat helpers: `backend/src/audit_workbench/extraction/ocr_chat.py`

- Adapter: `backend/src/audit_workbench/extraction/glm_ocr.py`
- Unit tests: `backend/tests/unit/extraction/test_glm_ocr.py`
- Live Gououiad: `backend/tests/live/platform/test_glm_gououiad_markdown.py` (`GLM_GOUOUIAD_LIVE=1`)

## Related

- [deploy/glmocr/README.md](../deploy/glmocr/README.md)
- [REPODY-VLM.md](./REPODY-VLM.md) — structured NuExtract / llama.cpp
- [PADDLEOCR-V6.md](./PADDLEOCR-V6.md) — PP-OCRv6 markdown OCR
- [COMMANDS.md](./COMMANDS.md)
