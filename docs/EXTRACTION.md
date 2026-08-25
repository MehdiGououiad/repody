# Document models (modular adapters)

Each catalog id is one **adapter** behind the shared extraction pipeline.
Workers call external servers; the backend does not ship model weights.

| Catalog id | Adapter | Official docs | Local serve | Worker needs |
|---|---|---|---|---|
| `repody:vlm` | `extraction/nuextract.py` | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) · [REPODY-VLM.md](./REPODY-VLM.md) | `pnpm llamacpp:serve` **:8081** | OpenAI-compat URL only |
| `paddleocr:qwen` | `extraction/paddleocr_qwen.py` | PP-OCR serving + Qwen text→JSON (UI schema) | `:8868` + `pnpm qwen35:serve` **:8084** | HTTP only |
| `glm:qwen` | `extraction/glm_ocr_qwen.py` | Official GlmOcr SDK markdown + Qwen text→JSON (same schema prompt as `paddleocr:qwen`) | `:8083` + `:8084` | **`otel,glmocr`** + Qwen URL |

Markdown-only OCR adapters (`paddleocr:v6`, `glm:ocr`) remain as **internal stages** for the
Qwen pipelines — they are **not** workflow catalog options.

**Official-docs posture**

| Path | Official contract | Notes |
|---|---|---|
| `repody:vlm` | NuExtract template JSON, PDF **170 DPI**, temp **0.2** | Vision token cap may be lower than HF defaults for VRAM |
| `paddleocr:qwen` | OCR official `POST /ocr`; JSON stage is **Repody** UI-schema prompt on Qwen (thin; no value post-process) | Shared `qwen_text.py` with `glm:qwen` |
| `glm:qwen` | Official GlmOcr SDK whole-page `Text Recognition:` then Qwen JSON | Set `AUDIT_GLM_OCR_LAYOUT_ENABLED=true` for PP-DocLayoutV3 |
| Qwen stage | Not a document-parse model | Text→JSON against workflow schema only — no OCR rewrite |

NuExtract structured JSON is stored verbatim in `run_documents.extraction_meta.rawText`;
leaf rows in `extracted_fields` are derived for UI/rules only.

## Automode (`nativePdfAuto`)

Per-document toggle (workflow UI). Not a catalog id — keep selecting `documentModelId`
as the OCR/VLM fallback.

| Step | Behavior |
|---|---|
| Input is not PDF | Skip inspector → selected model |
| PDF + Auto on | [pdf-inspector](https://github.com/firecrawl/pdf-inspector) `process_pdf_bytes` |
| Quality OK | Native markdown → Qwen text→JSON (same as `paddleocr:qwen`) |
| Quality weak | Selected `documentModelId` (`paddleocr:qwen` / `glm:qwen` / `repody:vlm`) |

**Accept native** only when all hold: `pdf_type == text_based`,
`confidence >= AUDIT_PDF_INSPECTOR_MIN_CONFIDENCE` (default `0.7`),
no encoding issues, empty `pages_needing_ocr`, markdown length
`>= AUDIT_PDF_INSPECTOR_MIN_CHARS` (default `40`).
`mixed` / `scanned` / `image_based` always fall back (v1 is all-or-nothing).

Decision is recorded on `extraction_meta.nativePdf`
(`source`, `pdfType`, `confidence`, `fallbackReason`).

Dependency: `pdf-inspector` on the extract worker. Missing package soft-fails to the
selected model.

## Local == prod packaging

| Layer | Local (`pnpm platform`) | Prod (Helm) |
|---|---|---|
| Extract worker | Hub image, or **local `otel,glmocr` build** when `--with-glm` | Backend image with extras you publish |
| Python extras | Hub = `otel` (lean). `--with-glm` → `compose.glmocr.yaml` builds `repody-backend:local-glmocr` with `otel,glmocr` | Set `REPODY_BACKEND_EXTRAS=otel,glmocr` when releasing if GLM is required |
| NuExtract / Paddle / GLM GGUF | Host scripts on `:8081` / `:8868` / `:8083` | External services; set Helm `config.*BaseUrl` and enable flags |

One command for all three structured paths:

```bash
pnpm platform -- --with-nuextract --with-glm
```

First `--with-glm` worker build downloads torch/layout wheels (official SDK).
