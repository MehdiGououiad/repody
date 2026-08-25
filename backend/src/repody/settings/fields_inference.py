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
    gpu_live_probe: bool = Field(
        default=False,
        description=(
            "Call inference /v1/models for catalog and diagnostics. "
            "Disable for remote or shared GPU if probes are costly."
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
        le=900.0,
        description=(
            "HTTP timeout for PP-OCRv6 POST /ocr. Must stay <= "
            "AUDIT_WORKER_TASK_TIMEOUT_MINUTES * 60."
        ),
    )
    paddleocr_v6_use_doc_orientation_classify: bool = Field(
        default=True,
        description=(
            "Official POST /ocr override for document orientation classification. "
            "Default true matches the exported OCR pipeline; set false for the "
            "documented fast path when inputs are already oriented."
        ),
    )
    paddleocr_v6_use_doc_unwarping: bool = Field(
        default=True,
        description=(
            "Official POST /ocr override for document unwarping. Default true "
            "matches the exported OCR pipeline; set false for clean documents."
        ),
    )
    paddleocr_v6_use_textline_orientation: bool = Field(
        default=True,
        description=(
            "Official POST /ocr override for text-line orientation. Default true "
            "matches the exported OCR pipeline; set false for the documented fast path."
        ),
    )

    paddleocr_qwen_enabled: bool = Field(
        default=True,
        description=(
            "Register PP-OCRv6 + Qwen (paddleocr:qwen) for structured extraction: "
            "official POST /ocr then Qwen text→JSON. Requires PP-OCRv6 (:8868) and "
            "Qwen llama-server (:8084)."
        ),
    )
    glm_ocr_qwen_enabled: bool = Field(
        default=False,
        description=(
            "Register GLM-OCR + Qwen (glm:qwen) for structured extraction: "
            "official GlmOcr SDK markdown then Qwen text→JSON. Requires GLM-OCR "
            "(:8083), Qwen (:8084), and worker extras otel,glmocr."
        ),
    )
    qwen35_base_url: str = Field(
        default="http://127.0.0.1:8084/v1",
        description=(
            "Qwen3.5 OpenAI-compatible API origin for paddleocr:qwen text→JSON. "
            "Default llama-server :8084/v1 (`pnpm qwen35:serve`)."
        ),
    )
    qwen35_served_model: str = Field(
        default="Qwen3.5-4B",
        description="Model id for Qwen chat/completions (llama-server -a alias).",
    )
    qwen35_timeout_seconds: float = Field(
        default=180.0,
        ge=30,
        le=900.0,
        description=(
            "HTTP timeout for Qwen text→JSON in paddleocr:qwen. Must stay <= "
            "AUDIT_WORKER_TASK_TIMEOUT_MINUTES * 60."
        ),
    )
    pdf_inspector_min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description=(
            "Automode (nativePdfAuto): accept Firecrawl pdf-inspector native "
            "markdown only when confidence >= this value (then Qwen JSON)."
        ),
    )
    pdf_inspector_min_chars: int = Field(
        default=40,
        ge=1,
        le=10_000,
        description=(
            "Automode: minimum stripped markdown length before accepting "
            "native PDF text (else fall back to the selected document model)."
        ),
    )

    glm_ocr_enabled: bool = Field(
        default=True,
        description=(
            "Register GLM-OCR (glm:ocr) as a markdown-only document model. "
            "Local default: zai-org GlmOcr SDK (PP-DocLayoutV3) + llama-server "
            "ggml-org/GLM-OCR-GGUF on AUDIT_GLM_OCR_BASE_URL (default :8083)."
        ),
    )
    glm_ocr_base_url: str = Field(
        default="http://127.0.0.1:8083/v1",
        description=(
            "OCR API origin for the official GlmOcr SDK. Default llama-server "
            ":8083/v1. Ollama uses http://127.0.0.1:11434 (no /v1)."
        ),
    )
    glm_ocr_served_model: str = Field(
        default="GLM-OCR",
        description="Model id for OCR requests (llama-server -a alias; Ollama: glm-ocr:latest).",
    )
    glm_ocr_timeout_seconds: float = Field(
        default=180.0,
        ge=30,
        le=900.0,
        description=(
            "HTTP timeout for GLM-OCR region OCR via the official SDK. Must stay <= "
            "AUDIT_WORKER_TASK_TIMEOUT_MINUTES * 60."
        ),
    )
    glm_ocr_layout_device: str = Field(
        default="cpu",
        description=(
            "Device for PP-DocLayoutV3 in the official SDK "
            "(cpu | cuda | cuda:N). Prefer cpu when the GPU hosts llama-server."
        ),
    )
    glm_ocr_layout_model_dir: str = Field(
        default="PaddlePaddle/PP-DocLayoutV3_safetensors",
        description=(
            "PP-DocLayoutV3 model id/path for the official GLM-OCR SDK "
            "(Hugging Face safetensors export)."
        ),
    )
    glm_ocr_layout_enabled: bool = Field(
        default=False,
        description=(
            "When false (default): official model-only path — whole page with "
            "'Text Recognition:' (no PP-DocLayoutV3). When true: GlmOcr SDK + "
            "PP-DocLayoutV3 region OCR (zai-org document-parsing pipeline)."
        ),
    )
    glm_ocr_sdk_max_workers: int = Field(
        default=1,
        ge=1,
        le=32,
        description=(
            "Official SDK region-OCR parallelism (pipeline.max_workers). "
            "Must stay <= llama-server -np (default 1) to avoid queue pile-up."
        ),
    )
    glm_ocr_pdf_max_pages: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional PDF page cap for official SDK page_loader.pdf_max_pages. "
            "Unset (default) matches glmocr config.yaml null — no silent truncation."
        ),
    )
    glm_ocr_id_card_profile: bool = Field(
        default=False,
        description=(
            "Optional GLM-OCR profile for photo-heavy ID cards: loads "
            "deploy/glmocr/config.idcard.yaml (OCR on image/chart regions) and "
            "enables region-text fallback when the official formatter is image-only."
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

    extraction_cache_enabled: bool = Field(
        default=False,
        description=(
            "Redis cache for extraction results. Default false so dev/benchmark runs "
            "always hit the model unless explicitly enabled."
        ),
    )
    extraction_cache_ttl_seconds: int = Field(default=86400, ge=60)

    structured_llm_enabled: bool = Field(
        default=False,
        description="Use instructor/Pydantic for structured JSON when available.",
    )

    progress_commit_interval_ms: int = Field(default=400)
