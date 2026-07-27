# ADR 002: Repody VLM with external inference

**Status:** Accepted  
**Date:** 2026-06-13  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Structured field extraction uses **Repody VLM** (image → JSON schema). Inference runs outside the Repody Helm release on an OpenAI-compatible **llama-server** endpoint (`AUDIT_LLAMACPP_*` env vars).

The product will add more document models later; routing must not hard-code a single endpoint.

## Decision

1. **Single catalog** in `catalog/registry.py` — each entry has `runtime` + `runtime_model`.
2. **Document extraction:** `AUDIT_INFERENCE_MODE=llamacpp` → `AUDIT_LLAMACPP_BASE_URL` (external OpenAI-compatible endpoint).
3. **Shared client code** in `inference/openai_compat.py` and `extraction/repody_vlm.py`.
4. **LLM rule validation** uses a separate small text model, never the document-model runtime.
5. **Live probes** live in `catalog/probes.py`.

Default catalog id: `repody:vlm`.

### Validation vs extraction runtime

| Concern | Runtime selector |
|---------|------------------|
| Document extraction | `AUDIT_INFERENCE_MODE` → external llama-server endpoint |
| LLM rule validation | `get_chat()` → validation model or stub |

## Consequences

**Positive**

- Matches NuExtract llama-server deployment for Repody VLM weights
- Adding a model is one registry entry plus endpoint configuration
- Health/diagnostics expose runtime-specific availability

**Negative**

- Operators run and monitor inference outside the Repody release

## Adding another document model

```python
# catalog/registry.py — _registered_models()
models["vendor:MyModel"] = DocumentModelSpec(
    id="vendor:MyModel",
    label="My Model",
    engine="document_model",
    runtime="llamacpp",  # or a dedicated runtime string
    runtime_model="org/MyModel",
    description="…",
    markdown_only=False,  # True for document→Markdown adapters
)
```

Register an adapter with `register_document_model_adapter(id, extract_fn)` and import the module from `extraction/pipeline.py`.

Examples:

- `repody:vlm` / `repody:vlm:cloud` — NuExtract structured (+ optional markdown)
- `paddleocr:v6` — PP-OCRv6 markdown via official `/ocr` ([docs/PADDLEOCR-V6.md](../PADDLEOCR-V6.md))
- `glm:ocr` — GLM-OCR markdown via llama-server ([docs/GLM-OCR.md](../GLM-OCR.md))

If the new model needs a different serve profile, point a dedicated base URL setting at that endpoint (do not hard-code inside the pipeline).

## References

- [docs/REPODY-VLM.md](../REPODY-VLM.md)
- [docs/PADDLEOCR-V6.md](../PADDLEOCR-V6.md)
- [docs/GLM-OCR.md](../GLM-OCR.md)
- [DEPLOY.md](../../DEPLOY.md)
- `backend/tests/test_inference/test_llamacpp_runtime.py`
