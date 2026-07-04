# ADR 002: Repody VLM with external inference

**Status:** Accepted  
**Date:** 2026-06-13  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Structured field extraction uses **Repody VLM** (image → JSON schema). Inference runs outside the Repody Helm release:

- **Local:** llama-server or vLLM on the host (`AUDIT_VLLM_*` env vars)
- **Production:** vLLM or llama-server

The product will add more document models later; routing must not hard-code a single endpoint.

## Decision

1. **Single catalog** in `extraction/model_registry.py` — each entry has `runtime` + `runtime_model`.
2. **Document extraction:** `AUDIT_INFERENCE_MODE=vllm` → `AUDIT_VLLM_BASE_URL` (external OpenAI-compatible endpoint).
3. **Shared client code** in `inference/openai_compat.py` and `extraction/repody_vlm.py`.
4. **LLM rule validation** uses a separate small text model, never the document-model runtime.
5. **Live probes** live in `catalog/probes.py`.

Default catalog id: `repody:vlm`.

### Validation vs extraction runtime

| Concern | Runtime selector |
|---------|------------------|
| Document extraction | `AUDIT_INFERENCE_MODE` → external vLLM-compatible endpoint |
| LLM rule validation | `get_inference_client()` → separate text model or stub |

## Consequences

**Positive**

- Matches upstream vLLM deployment notes for Repody VLM weights
- Adding a model is one registry entry plus endpoint configuration
- Health/diagnostics expose runtime-specific availability

**Negative**

- Operators run and monitor inference outside the Repody release

## Adding another document model

```python
# extraction/model_registry.py — _registered_models()
models["vendor:MyModel"] = DocumentModelSpec(
    id="vendor:MyModel",
    label="My Model",
    engine="document_model",
    runtime="vllm",
    runtime_model="org/MyModel",
    description="…",
)
```

If the new model needs a different serve profile, point `AUDIT_VLLM_BASE_URL` at a dedicated endpoint (or add per-model base URLs in the registry).

## References

- [docs/REPODY-VLM.md](../REPODY-VLM.md)
- [DEPLOY.md](../../DEPLOY.md)
- `backend/tests/test_inference/test_vllm_runtime.py`
