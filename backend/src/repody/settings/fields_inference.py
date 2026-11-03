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
        le=900.0,
        description=(
            "VLM HTTP client ceiling in seconds. Must stay <= "
            "AUDIT_WORKER_TASK_TIMEOUT_MINUTES * 60."
        ),
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
            "Optional path to a document for VLM warmup. "
            "When unset, a synthetic 1x1 PNG is used (no product fixture)."
        ),
    )
    healthz_probe_inference: bool = Field(
        default=False,
        description=(
            "Probe llama-server on GET /v1/healthz. Keep false so healthchecks "
            "do not load the inference service."
        ),
    )
    repody_vlm_markdown_on_extract: bool = Field(
        default=False,
        description=(
            "When true, run NuExtract markdown mode alongside structured extraction "
            "(second model call). Markdown-only workflows still use markdown when "
            "the document has no schema fields. Default false — official NuExtract "
            "treats structured and markdown as separate calls."
        ),
    )
    repody_vlm_max_pages_per_request: int | None = Field(
        default=None,
        ge=1,
        le=64,
        description=(
            "Optional client-side NuExtract page cap. None = send all PDF pages "
            "(official examples). Set e.g. 6 when llama.cpp uses --limit-mm-per-prompt image:6."
        ),
    )
    repody_vlm_enable_thinking: bool = Field(
        default=False,
        description=(
            "NuExtract enable_thinking. When true, structured temperature uses 0.6 "
            "and markdown uses 0.7 (official thinking / reasoning examples)."
        ),
    )

    extraction_cache_enabled: bool = Field(
        default=False,
        description=(
            "Redis cache for extraction results. Default false so dev/benchmark runs "
            "always hit the model unless explicitly enabled."
        ),
    )
    extraction_cache_ttl_seconds: int = Field(default=86400, ge=60)

    progress_commit_interval_ms: int = Field(default=400)
