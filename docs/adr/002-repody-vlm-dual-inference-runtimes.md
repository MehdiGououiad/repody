# ADR 002: Repody document models with multi-runtime inference

**Status:** Accepted  
**Date:** 2026-06-13  
**Updated:** 2026-09-07  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Structured field extraction uses pluggable **document models** (image/PDF → JSON schema or markdown). Inference runs outside the Repody Helm release on runtime-specific endpoints. Routing must not hard-code a single endpoint or a dual-runtime story.

## Decision

1. **Single catalog** in `catalog/registry.py` — each entry has `runtime` + `runtime_model`, gated by settings flags. Catalog entries are **workflow-selectable structured Document models** only.
2. **Runtime catalog** (as of this ADR refresh):

| Runtime id | Typical catalog id | Role |
|------------|--------------------|------|
| `llamacpp` | `repody:vlm` | Local OpenAI-compatible llama-server (NuExtract) |
| `nuextract_cloud` | `repody:vlm:cloud` | Official NuExtract cloud REST |
| `paddleocr_qwen` | `paddleocr:qwen` | PP-OCRv6 + Qwen text→JSON |
| `glm_ocr_qwen` | `glm:qwen` | GLM-OCR SDK markdown + Qwen text→JSON |

**Internal markdown OCR stages** (not catalog / not workflow-selectable):

| Stage id | Used by | Role |
|----------|---------|------|
| `paddleocr:v6` | `paddleocr:qwen` | PP-OCRv6 markdown via PaddleX `/ocr` |
| `glm:ocr` | `glm:qwen` | GLM-OCR markdown via official SDK + llama-server |

Helpers (`fetch_*_markdown` / `extract_with_*`) live in `extraction/paddleocr_v6.py` and `extraction/glm_ocr.py` for direct import by Qwen Document models, benchmarks, and live tests. They do **not** call `register_document_model_adapter`.

3. **Shared client / adapters:** OpenAI-compatible HTTP in `inference/openai_compat.py`; Repody VLM adapter in `extraction/vlm.py` (not a legacy `repody_vlm.py` module). Structured models register adapters from `extraction/register.py` (imported by `extraction/pipeline.py`).
4. **LLM rule validation** uses a separate small text model (`get_chat()`), never the document-model runtime.
5. **Live probes** live in `catalog/probes.py`.

Default catalog id when enabled: `repody:vlm`.

### Validation vs extraction runtime

| Concern | Runtime selector |
|---------|------------------|
| Document extraction | Catalog entry `runtime` + per-runtime settings (`AUDIT_LLAMACPP_*`, cloud/Paddle/GLM flags) |
| LLM rule validation | `get_chat()` → validation model or stub |

Global `AUDIT_INFERENCE_MODE` may still exist as a legacy / operator shorthand; **catalog-first routing** (model id → runtime) is the source of truth for which endpoint a document uses.

## Consequences

**Positive**

- Adding a structured Document model is one registry entry plus endpoint configuration
- Health/diagnostics expose runtime-specific availability
- Internal markdown OCR stages stay callable without sharing the selectable catalog seam

**Negative**

- Operators run and monitor inference outside the Repody release
- Multiple runtime configs increase ops surface
- OCR stage settings (`AUDIT_PADDLEOCR_V6_*`, `AUDIT_GLM_OCR_*`) gate stage availability/probes separately from catalog registration

## Adding another document model

```python
# catalog/registry.py — _registered_models()
models["vendor:MyModel"] = DocumentModelSpec(
    id="vendor:MyModel",
    label="My Model",
    engine="document_model",
    runtime="llamacpp",  # or paddleocr_qwen / glm_ocr_qwen / …
    runtime_model="org/MyModel",
    description="…",
    markdown_only=False,
)
```

Register an adapter with `register_document_model_adapter(id, extract_fn)` and import the module from `extraction/register.py`.

Examples (workflow-selectable Document models):

- `repody:vlm` / `repody:vlm:cloud` — NuExtract structured (+ optional markdown)
- `paddleocr:qwen` — OCR stage + Qwen structured extraction ([docs/PADDLEOCR-V6.md](../PADDLEOCR-V6.md))
- `glm:qwen` — GLM-OCR stage + Qwen structured extraction ([docs/GLM-OCR.md](../GLM-OCR.md))

Internal OCR stages (direct helpers only — not catalog entries):

- `paddleocr:v6` — PP-OCRv6 markdown via official `/ocr`
- `glm:ocr` — GLM-OCR markdown via llama-server / official SDK

If the new model needs a different serve profile, point a dedicated base URL setting at that endpoint (do not hard-code inside the pipeline).

## References

- [docs/REPODY-VLM.md](../REPODY-VLM.md)
- [docs/PADDLEOCR-V6.md](../PADDLEOCR-V6.md)
- [docs/GLM-OCR.md](../GLM-OCR.md)
- [DEPLOY.md](../../DEPLOY.md)
- `backend/src/repody/catalog/registry.py`
- `backend/src/repody/extraction/vlm.py`
- `backend/tests/test_inference/test_llamacpp_runtime.py`
