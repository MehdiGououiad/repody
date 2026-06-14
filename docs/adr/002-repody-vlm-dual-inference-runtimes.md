# ADR 002: Repody VLM with dual inference runtimes

**Status:** Accepted  
**Date:** 2026-06-13  
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

Structured field extraction uses **Repody VLM** (image → JSON schema). Deploy targets differ:

- **Developer laptops / CPU servers:** Docker Desktop Model Runner + llama.cpp GGUF
- **GPU servers:** vLLM with the upstream vision weights and MTP speculative decoding

The product will add more document models later; routing must not hard-code a single endpoint.

## Decision

1. **Single catalog** in `extraction/model_registry.py` — each entry has `runtime` + `runtime_model`.
2. **Two OpenAI-compatible runtimes**, selected by `AUDIT_INFERENCE_MODE`:
   - `docker_model_runner` → `AUDIT_DOCKER_MODEL_RUNNER_BASE_URL`
   - `vllm` → `AUDIT_VLLM_BASE_URL`
3. **Compose overlays:**
   - CPU: `compose.cpu.yaml` (Model Runner tuning, no vLLM container)
   - GPU: `compose.gpu.yaml` adds `vllm` service; sets `AUDIT_INFERENCE_MODE=vllm` on api/worker
4. **Shared client code** in `inference/openai_compat.py` and `extraction/repody_vlm.py` (legacy module name).
5. **LLM rule validation** stays on a separate small text model (Model Runner), never on the document-model runtime — even when `AUDIT_INFERENCE_MODE=vllm`.
6. **Live probes** live in `services/document_model_catalog.py` (not HTTP routers).

Default catalog id: `repody:vlm` (legacy alias `repody:vlm`).

### Validation vs extraction runtime

| Concern | Runtime selector |
|---------|------------------|
| Document extraction | `AUDIT_INFERENCE_MODE` → DMR or vLLM |
| LLM rule validation | `get_inference_client()` → DMR or stub always |

This is intentional: validation uses a small text model; vLLM hosts the vision document model only.

## Consequences

**Positive**

- GPU path matches upstream vLLM deployment notes for Repody VLM weights
- Adding a model is one registry entry + optional new compose service if it needs a different serve profile
- Health/diagnostics expose runtime-specific availability

**Negative**

- GPU deploy always chains `compose.cpu.yaml` + `compose.gpu.yaml` (worker-fast, Hatchet tuning live in CPU base)
- Two compose commands to document (`docker:deploy` vs `docker:deploy:gpu`)
- “OCR” naming in API/settings is a legacy alias for document models

## Alternatives considered

| Option | Why not |
|--------|---------|
| Model Runner for GPU too | Slower than vLLM on hardware we target |
| Single vLLM everywhere | Heavy for laptop dev; Model Runner integrates with Docker Desktop |
| Per-model microservices from day one | Premature; registry pattern suffices until multiple concurrent models are required |

## Adding another document model

```python
# extraction/model_registry.py — _registered_models()
models["vendor:MyModel"] = DocumentModelSpec(
    id="vendor:MyModel",
    label="My Model",
    engine="document_model",
    runtime="vllm",  # or docker_model_runner
    runtime_model="org/MyModel",
    description="…",
)
```

If the new model needs different vLLM flags, add a dedicated compose service and point `AUDIT_VLLM_BASE_URL` (or introduce per-model base URLs in the registry).

## References

- [DEPLOY.md](../../DEPLOY.md#gpu-stack-repody-vlm-via-vllm)
- [docs/REPODY-VLM.md](../REPODY-VLM.md)
- [docs/OCR_CPU.md](../OCR_CPU.md)
- `compose.gpu.yaml`, `backend/tests/test_inference/test_vllm_runtime.py`
