# GLM-OCR (host llama-server)

Host `llama-server` for catalog id `glm:ocr` (markdown-only).

Base model: [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR).  
GGUF pack: [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF).

Chat contract (zai-org): **image first**, then text prompt **`Text Recognition:`**.

## Commands

```powershell
pnpm glmocr:serve      # -hf ggml-org/GLM-OCR-GGUF on :8083
pnpm glmocr:verify
pnpm glmocr:stop
pnpm glmocr:download   # optional local GGUFs under deploy/glmocr/models/
```

## Platform env

```env
AUDIT_GLM_OCR_ENABLED=true
AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:8083/v1
AUDIT_GLM_OCR_SERVED_MODEL=GLM-OCR
```

Compose workers use `http://host.docker.internal:8083/v1`. Rebuild the extract worker after enabling (`pnpm dev:worker:rebuild`).

## Notes

- Port **8083** (NuExtract **:8081**, PP-OCRv6 **:8868**).
- Started by `pnpm dev:all` when `AUDIT_GLM_OCR_ENABLED=true` (skip with `--no-glmocr`).
- Docs: [docs/GLM-OCR.md](../../docs/GLM-OCR.md)
