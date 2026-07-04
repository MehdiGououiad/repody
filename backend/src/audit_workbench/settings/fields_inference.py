from __future__ import annotations

from pydantic import Field


class InferenceSettingsFields:
    extractor: str = Field(
        default="pipeline",
        description="pipeline (document model extraction) | stub",
    )
    inference_mode: str = Field(
        default="docker_model_runner",
        description="docker_model_runner (CPU / Model Runner) | vllm (GPU official serve) | stub",
    )
    docker_model_runner_base_url: str = Field(
        default="http://model-runner.docker.internal/engines/llama.cpp/v1",
        description="OpenAI-compatible Docker Model Runner endpoint.",
    )
    vllm_base_url: str = Field(
        default="http://vllm:8000/v1",
        description="OpenAI-compatible vLLM endpoint for Repody VLM (GPU).",
    )
    vllm_api_key: str | None = Field(
        default=None,
        description="Optional bearer token when vLLM is behind auth.",
    )
    vllm_served_model: str = Field(
        default="numind/NuExtract3",
        description="Model id served by vLLM (upstream weights for Repody VLM).",
    )

    default_ocr_model: str = Field(
        default="repody:vlm",
        description="Default document model id from the registry.",
    )
    repody_vlm_enabled: bool = Field(
        default=True,
        description="Register Repody VLM in the document model catalog.",
    )
    repody_vlm_model: str = Field(
        default="repody/repody-vlm:q4_k_m-16k",
        description="Repody VLM model id in Docker Model Runner.",
    )
    repody_vlm_max_tokens: int = Field(default=512, ge=64)
    repody_vlm_max_edge_px: int | None = Field(
        default=None,
        ge=512,
        description="Optional Repody VLM page downscale cap. None follows NuExtract docs and preserves rendered size.",
    )
    repody_vlm_pdf_dpi: int = Field(
        default=170,
        ge=72,
        description="PDF raster DPI per NuExtract3 official example (lossless PNG).",
    )
    repody_vlm_jpeg_quality: int = Field(
        default=95,
        ge=50,
        le=100,
        description="Fallback JPEG quality for non-PDF/non-image inputs.",
    )
    repody_vlm_timeout_seconds: float = Field(default=600.0, ge=30)
    repody_vlm_warmup_on_start: bool = Field(
        default=False,
        description=(
            "Warm Repody VLM when OCR workers start. Disabled by default to avoid "
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
            "Probe GPU/vLLM on GET /v1/healthz. Keep false so healthchecks "
            "do not load the inference service."
        ),
    )
    gpu_live_probe: bool = Field(
        default=False,
        description=(
            "Call vLLM /v1/models for catalog and diagnostics. "
            "Disable for remote or shared GPU if probes are costly."
        ),
    )
    repody_vlm_max_pages_per_request: int = Field(
        default=6,
        ge=1,
        description=(
            "Max rendered pages sent in one Repody VLM request. "
            "Cap pages to stay within model context."
        ),
    )
    repody_vlm_markdown_on_extract: bool = Field(
        default=True,
        description=(
            "Platform switch: allow NuExtract document-to-Markdown when a workflow "
            "document enables markdown extraction."
        ),
    )
    repody_vlm_markdown_max_tokens: int = Field(
        default=8192,
        ge=256,
        description="Completion token budget for NuExtract markdown conversion.",
    )
    repody_vlm_enable_thinking: bool = Field(
        default=False,
        description=(
            "NuExtract reasoning mode for difficult layouts (enable_thinking). "
            "Uses higher temperature per upstream docs."
        ),
    )

    ocr_max_pages: int = Field(default=10, description="Max PDF pages per document.")
    ocr_max_pages_hard_cap: int = Field(default=50)
    document_render_max_edge_px: int = Field(
        default=896,
        description="Longest image edge when rasterizing documents for bundle cache.",
    )
    document_render_pdf_dpi: int = Field(
        default=120,
        description="PDF rasterization DPI for bundle cache.",
    )
    ocr_jpeg_quality: int = 82
    ocr_jpeg_optimize: bool = Field(
        default=True,
        description="PIL JPEG optimize pass (slower encode, smaller files). Disabled for VLM renders.",
    )

    llm_validation_enabled: bool = Field(
        default=False,
        description="Enable LLM rule validation (requires validation_model in Docker Model Runner).",
    )
    validation_model: str | None = Field(
        default=None,
        description=(
            "Docker Model Runner text model id for LLM rule validation. "
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

    parallel_doc_extraction: bool | None = Field(
        default=None,
        description=(
            "Extract multiple documents concurrently. None = auto "
            "(sequential for docker_model_runner CPU; parallel for vllm). "
            "Set true to force parallel; false to force sequential."
        ),
    )
    parallel_storage_fetch: bool = True
    progress_commit_interval_ms: int = Field(default=400)
