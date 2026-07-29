# Document models (modular adapters)

Each catalog id is one **adapter** behind the shared extraction pipeline.
Workers call external servers; the backend does not ship model weights.

| Catalog id | Adapter | Official docs | Local serve | Worker needs |
|---|---|---|---|---|
| `repody:vlm` | `extraction/nuextract.py` | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) · [REPODY-VLM.md](./REPODY-VLM.md) | `pnpm llamacpp:serve` **:8081** | OpenAI-compat URL only |
| `paddleocr:v6` | `extraction/paddleocr_v6.py` | [PaddleOCR Serving](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html) · [PADDLEOCR-V6.md](./PADDLEOCR-V6.md) | `pnpm paddleocr:v6:serve` **:8868** | HTTP client only |
| `glm:ocr` | `extraction/glm_ocr.py` + `glm_ocr_sdk.py` | [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) · [GLM-OCR.md](./GLM-OCR.md) | `pnpm glmocr:serve` **:8083** | Image extras **`otel,glmocr`** (CPU torch) + llama URL |

Shared seams: `catalog/registry.py` (register), `catalog/adapters.py` (dispatch),
`extraction/pipeline.py` (run path), `extraction/branding.py` (public ids).

**Official-docs posture:** adapters call models as documented. NuExtract structured
JSON is stored verbatim in `run_documents.extraction_meta.rawText`; leaf rows in
`extracted_fields` are derived for UI/rules only. No document-specific heuristics
in runtime extraction.

## Local == prod packaging

| Layer | Local (`pnpm dev:all`) | Prod (Helm) |
|---|---|---|
| Extract worker | Compose `worker-extract` | Deployment `*-worker-extract` |
| Python extras | `REPODY_BACKEND_EXTRAS=otel,glmocr` (Compose + `pnpm images:build` default) | Same in the backend image |
| NuExtract / Paddle / GLM GGUF | Host scripts on `:8081` / `:8868` / `:8083` | External services; set Helm `config.*BaseUrl` and enable flags |

One command locally: `pnpm dev:all` (no native extract swap). First worker rebuild
with `glmocr` downloads torch/layout wheels — same content as the release image.
