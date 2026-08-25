# GLM-OCR (markdown-only)

Catalog ids:
- `glm:ocr` — Document → text/Markdown via the **official zai-org SDK**
  ([GlmOcr](https://huggingface.co/zai-org/GLM-OCR)). Default: whole-page
  `Text Recognition:` (no layout). Opt-in PP-DocLayoutV3 with
  `AUDIT_GLM_OCR_LAYOUT_ENABLED=true`.
- `glm:qwen` — same official SDK markdown, then **Qwen3.5 text→JSON** against the
  workflow UI schema (same second stage as `paddleocr:qwen`).

Enable structured: `AUDIT_GLM_OCR_QWEN_ENABLED=true` (and `pnpm qwen35:serve`).

## Official sources

| Role | Link |
|---|---|
| Model card (SDK recommended) | [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) |
| SDK source / config | [github.com/zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR) |
| Official self-host (NVIDIA) | **vLLM / SGLang** with `zai-org/GLM-OCR` BF16 |
| Official local / CPU (zai-org) | **[Ollama](https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md)** — optional here via `pnpm glmocr:ollama:serve` |
| **This repo default** | [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF) via `llama-server` (**F16**) |
| Layout model | [PP-DocLayoutV3_safetensors](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_safetensors) |

> Local default is **llama-server** on `:8083` (Vulkan/CPU/CUDA). This is the
> user's selected community GGUF runtime, not zai-org's documented vLLM/SGLang
> NVIDIA or Ollama CPU runtime. The SDK/API contract remains official; the
> runtime choice is intentionally documented as a deviation.
> Profile: `deploy/glmocr/config.selfhosted.yaml` (official layout mapping).
> Optional ID-card profile: `AUDIT_GLM_OCR_ID_CARD_PROFILE=true` loads
> `deploy/glmocr/config.idcard.yaml` (OCR on `image`/`chart` regions + region-text fallback).

## Install

```powershell
pnpm dev:all
# or after code/deps change:
pnpm dev:worker:rebuild
```

Host Python (tests / scripts):

```powershell
cd backend
uv sync --extra glmocr
```

## Env

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
# Optional — photo-heavy ID cards (CNIE, etc.)
AUDIT_GLM_OCR_ID_CARD_PROFILE=false
# Qwen stage (shared with paddleocr:qwen)
AUDIT_QWEN35_BASE_URL=http://127.0.0.1:8084/v1
AUDIT_QWEN35_SERVED_MODEL=Qwen3.5-4B
```

Warmup is opt-in: `GLMOCR_WARMUP=on` when running `pnpm glmocr:serve`.

Extract workers use `http://host.docker.internal:8083/v1`.

## Start

```powershell
pnpm glmocr:serve
pnpm glmocr:verify
pnpm glmocr:warmup
pnpm glmocr:stop
```

Optional Ollama instead:

```powershell
pnpm glmocr:ollama:serve
# then set AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:11434
# and AUDIT_GLM_OCR_SERVED_MODEL=glm-ocr:latest
```

## Contract (official SDK)

**Model-only (default):**

- `AUDIT_GLM_OCR_LAYOUT_ENABLED=false` (default)
- Whole-page `Text Recognition:` via the SDK Pipeline (no PP-DocLayoutV3).
  Matches HF transformers / Ollama examples.

**Document parsing (opt-in — zai-org recommended for complex layouts):**

- `AUDIT_GLM_OCR_LAYOUT_ENABLED=true`
- `GlmOcr(mode="selfhosted")` → PP-DocLayoutV3 → OCR with
  `Text Recognition:` / `Table Recognition:` / `Formula Recognition:`

Shared:

- llama-server: `api_mode=openai`, `/v1/chat/completions`, model alias `GLM-OCR`
- Sampling: `temperature=0.0`, `top_p=0.00001`, `top_k=1`, `repetition_penalty=1.1`
- PDF raster: **200 DPI**

## Related

- [deploy/glmocr/README.md](../deploy/glmocr/README.md)
- [EXTRACTION.md](./EXTRACTION.md)
- [COMMANDS.md](./COMMANDS.md)
