from __future__ import annotations

from pydantic import Field


class InferenceSettingsFields:
    extractor: str = Field(
        default="pipeline",
        description="pipeline (document model extraction) | stub",
    )
    inference_mode: str = Field(
        default="llamacpp",
        description="llamacpp (local llama-server OpenAI API) | stub",
    )
    llamacpp_base_url: str = Field(
        default="http://127.0.0.1:8081/v1",
        description="OpenAI-compatible llama-server endpoint for document extraction.",
    )
    llamacpp_api_key: str | None = Field(
        default=None,
        description="Optional bearer token when the inference endpoint requires auth.",
    )
    llamacpp_served_model: str = Field(
        default="nuextract3-q4_k_m",
        description="Model id served by llama-server (NuExtract3-Q4_K_M alias from /v1/models).",
    )

    default_document_model_id: str = Field(
        default="repody:vlm",
        description="Default document model id from the registry.",
    )
    repody_vlm_enabled: bool = Field(
        default=True,
        description="Register Repody VLM in the document model catalog.",
    )
    repody_vlm_timeout_seconds: float = Field(
        default=180.0,
        ge=30,
        le=180.0,
        description="VLM HTTP client ceiling; must not exceed worker task timeout.",
    )
    repody_vlm_warmup_on_start: bool = Field(
        default=False,
        description=(
            "Warm Repody VLM when extract workers start. Disabled by default to avoid "
            "unexpected native-worker calls to local or serverless inference endpoints."
        ),
    )
    repody_vlm_warmup_document: str | None = Field(
        default=None,
        description=(
            "Optional path to a fixture document for VLM warmup. "
            "Defaults to e2e/fixtures/documents/Facture.pdf at repo root."
        ),
    )
    healthz_probe_inference: bool = Field(
        default=False,
        description=(
            "Probe llama-server on GET /v1/healthz. Keep false so healthchecks "
            "do not load the inference service."
        ),
    )
    gpu_live_probe: bool = Field(
        default=False,
        description=(
            "Call inference /v1/models for catalog and diagnostics. "
            "Disable for remote or shared GPU if probes are costly."
        ),
    )
    repody_vlm_markdown_on_extract: bool = Field(
        default=True,
        description=(
            "Platform switch: allow NuExtract document-to-Markdown when a workflow "
            "document enables markdown extraction."
        ),
    )

    nuextract_cloud_enabled: bool = Field(
        default=False,
        description=(
            "Register NuExtract Cloud (repody:vlm:cloud) in the document model catalog. "
            "Requires AUDIT_NUEXTRACT_CLOUD_API_KEY."
        ),
    )
    nuextract_cloud_api_key: str | None = Field(
        default=None,
        description="Bearer API key for https://nuextract.ai (Authorization: Bearer …).",
    )
    nuextract_cloud_base_url: str = Field(
        default="https://nuextract.ai",
        description="NuExtract platform API origin (no trailing path).",
    )
    nuextract_cloud_project_id: str | None = Field(
        default=None,
        description=(
            "Optional fixed structured-extraction project id (sprj_…). "
            "When unset, each request creates a temporary project from the workflow template."
        ),
    )
    nuextract_cloud_timeout_seconds: float = Field(
        default=180.0,
        ge=30,
        le=600.0,
        description="HTTP/SSE timeout for NuExtract cloud jobs.",
    )

    paddleocr_v6_enabled: bool = Field(
        default=True,
        description=(
            "Register PP-OCRv6 (paddleocr:v6) as a markdown-only document model. "
            "Requires a running PaddleX OCR service "
            "(`paddlex --serve --pipeline OCR`, default model PP-OCRv6_medium)."
        ),
    )
    paddleocr_v6_base_url: str = Field(
        default="http://127.0.0.1:8868",
        description=(
            "PP-OCRv6 OCR API origin (no path). Client calls POST /ocr. "
            "Default :8868 avoids clashing with Keycloak (:8080)."
        ),
    )
    paddleocr_v6_timeout_seconds: float = Field(
        default=180.0,
        ge=30,
        le=600.0,
        description="HTTP timeout for PP-OCRv6 POST /ocr.",
    )

    glm_ocr_enabled: bool = Field(
        default=True,
        description=(
            "Register GLM-OCR (glm:ocr) as a markdown-only document model. "
            "Requires llama-server with ggml-org/GLM-OCR-GGUF on "
            "AUDIT_GLM_OCR_BASE_URL (default :8083)."
        ),
    )
    glm_ocr_base_url: str = Field(
        default="http://127.0.0.1:8083/v1",
        description=(
            "GLM-OCR OpenAI-compatible API origin (include /v1). "
            "Default :8083 avoids Keycloak (:8080) and NuExtract (:8081)."
        ),
    )
    glm_ocr_served_model: str = Field(
        default="GLM-OCR",
        description="Model id / alias returned by GLM-OCR llama-server /v1/models.",
    )
    glm_ocr_timeout_seconds: float = Field(
        default=180.0,
        ge=30,
        le=600.0,
        description="HTTP timeout for GLM-OCR chat/completions.",
    )

    llm_validation_enabled: bool = Field(
        default=False,
        description="Enable LLM rule validation (requires validation_model on the inference endpoint).",
    )
    validation_model: str | None = Field(
        default=None,
        description=(
            "Text model id for LLM rule validation on the inference endpoint. "
            "Required when LLM validation is enabled."
        ),
    )
    validation_max_tokens: int = Field(default=128, ge=32)
    validation_timeout_seconds: float = Field(default=60.0, ge=5.0)

    extraction_cache_enabled: bool = True
    extraction_cache_ttl_seconds: int = 86400

    structured_llm_enabled: bool = Field(
        default=False,
        description="Use instructor/Pydantic for structured JSON when available.",
    )

    progress_commit_interval_ms: int = Field(default=400)
