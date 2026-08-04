# GLM-OCR (host llama-server)

Host `llama-server` for catalog id `glm:ocr` (markdown-only).

Base model: [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR).  
GGUF pack: [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF).

Platform extraction uses the **official SDK** (`GlmOcr` + PP-DocLayoutV3). OCR
region calls hit this llama-server (`api_mode: openai`).

## Commands

```powershell
pnpm glmocr:serve      # -hf ggml-org/GLM-OCR-GGUF:F16 on :8083
pnpm glmocr:verify
pnpm glmocr:stop
pnpm glmocr:download   # optional local GGUFs under deploy/glmocr/models/
```

Optional zai-org CPU path (Ollama): `pnpm glmocr:ollama:serve` — then point env at
`:11434` and `glm-ocr:latest`.

## Platform env

```env
AUDIT_GLM_OCR_ENABLED=true
AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:8083/v1
AUDIT_GLM_OCR_SERVED_MODEL=GLM-OCR
AUDIT_GLM_OCR_LAYOUT_DEVICE=cpu
# Optional — CNIE / photo-heavy ID cards
AUDIT_GLM_OCR_ID_CARD_PROFILE=false
```

Warmup is opt-in: `GLMOCR_WARMUP=on` when running `pnpm glmocr:serve`, or `pnpm glmocr:warmup`.

Compose workers use `http://host.docker.internal:8083/v1`. Extract worker image
defaults to `BACKEND_EXTRAS=otel,glmocr` (official SDK). Rebuild after changes:
`pnpm dev:worker:rebuild`.

## Notes

- Port **8083** (NuExtract **:8081**, PP-OCRv6 **:8868**).
- Started by `pnpm dev:all` when `AUDIT_GLM_OCR_ENABLED=true` (skip with `--no-glmocr`).

## Related

- Modular catalog map: [docs/EXTRACTION.md](../../docs/EXTRACTION.md)
- Docs: [docs/GLM-OCR.md](../../docs/GLM-OCR.md)
