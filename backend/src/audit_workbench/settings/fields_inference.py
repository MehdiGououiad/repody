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
