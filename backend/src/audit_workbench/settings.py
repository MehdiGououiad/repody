from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUDIT_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Repody"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://audit:audit@localhost:5432/audit_workbench"
    )
    db_pool_size: int = Field(default=5, description="SQLAlchemy async pool size per process.")
    db_max_overflow: int = Field(default=10, description="Extra DB connections beyond pool_size.")
    db_pool_timeout: int = Field(default=30, description="Seconds to wait for a DB connection.")
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(
        default=20,
        description="Shared Redis pool size (cache + SSE pub/sub).",
    )

    hatchet_client_token: str | None = Field(
        default=None,
        description="Hatchet API token for workflow dispatch and workers.",
    )
    hatchet_client_host_port: str = Field(
        default="localhost:7077",
        description="Hatchet engine gRPC host:port.",
    )
    hatchet_client_tls_strategy: str = Field(
        default="none",
        description="TLS strategy for Hatchet gRPC (none for in-cluster hatchet-stack).",
    )
    hatchet_task_timeout_minutes: int = Field(
        default=3,
        description="Max minutes for a Hatchet audit-run task before cancellation.",
    )
    worker_pool_fast: str = Field(default="fast", description="Hatchet worker label for fast runs.")
    worker_pool_ocr: str = Field(default="ocr", description="Hatchet worker label for OCR runs.")

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    oidc_enabled: bool = Field(
        default=False,
        description="Require Keycloak JWT on management endpoints (disable for local pytest).",
    )
    oidc_issuer: str | None = Field(
        default=None,
        description="OIDC issuer URL, e.g. http://keycloak:8080/realms/repody",
    )
    oidc_issuer_aliases_env: str = Field(
        default="",
        validation_alias=AliasChoices("OIDC_ISSUER_ALIASES"),
        description="Comma-separated or JSON list of extra accepted JWT issuers.",
    )

    def accepted_oidc_issuer_aliases(self) -> list[str]:
        raw = self.oidc_issuer_aliases_env or os.environ.get("AUDIT_OIDC_ISSUER_ALIASES", "")
        return self._parse_oidc_issuer_aliases(raw)

    @staticmethod
    def _parse_oidc_issuer_aliases(value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    inner = text.strip("[]")
                    return [part.strip() for part in inner.split(",") if part.strip()]
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            return [part.strip() for part in text.split(",") if part.strip()]
        return []
    oidc_audience: str | None = Field(
        default=None,
        description="Optional JWT audience (client id). When unset, audience is not verified.",
    )
    oidc_jwks_url: str | None = Field(
        default=None,
        description="JWKS URL override. Defaults to {issuer}/protocol/openid-connect/certs",
    )
    oidc_jwks_json: str | None = Field(
        default=None,
        description="Inline JWKS JSON for tests (skips live JWKS fetch).",
    )

    keycloak_admin_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_ADMIN_URL", "KEYCLOAK_ADMIN_URL"),
        description="Keycloak base URL for Admin REST API (e.g. http://keycloak:8080).",
    )
    keycloak_admin_user: str = Field(
        default="admin",
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_ADMIN_USER", "KEYCLOAK_ADMIN_USER"),
    )
    keycloak_admin_password: str = Field(
        default="admin",
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_ADMIN_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD"),
    )
    keycloak_realm: str = Field(
        default="repody",
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_REALM", "KEYCLOAK_REALM"),
    )
    keycloak_admin_console_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUDIT_KEYCLOAK_ADMIN_CONSOLE_URL",
            "KEYCLOAK_ADMIN_CONSOLE_URL",
        ),
        description="Browser URL for the Keycloak admin console.",
    )
    keycloak_oauth_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_CLIENT_ID", "AUTH_KEYCLOAK_ID"),
        description="OAuth client id for operator benchmark password-grant tokens.",
    )
    keycloak_oauth_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUDIT_KEYCLOAK_CLIENT_SECRET",
            "AUTH_KEYCLOAK_CLIENT_SECRET",
        ),
        description="OAuth client secret for operator benchmark password-grant tokens.",
    )
    operator_benchmark_bearer_token: str | None = Field(
        default=None,
        description="Pre-issued bearer token for benchmark_suite.py (skips Keycloak grant).",
    )
    operator_benchmark_user: str | None = Field(
        default=None,
        description="Keycloak user for operator benchmark jobs when OIDC is enabled.",
    )
    operator_benchmark_password: str | None = Field(
        default=None,
        description="Keycloak password for operator benchmark jobs when OIDC is enabled.",
    )

    deployment_environment: str = Field(
        default="development",
        description="Deployment label attached to logs and traces (e.g. production).",
    )
    run_migrations_on_startup: bool = Field(
        default=False,
        description="Run Alembic upgrade head before serving (Docker entrypoint).",
    )

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "audit-documents"
    minio_secure: bool = False
    minio_public_endpoint: str | None = Field(
        default=None,
        description=(
            "Browser-reachable MinIO host:port for presigned upload URLs (e.g. localhost:9000)."
        ),
    )
    storage_backend: str = Field(default="local", description="local | s3")
    local_storage_path: str = Field(default=".data/storage")

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
    repody_vlm_warmup_on_start: bool = True
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

    surya_ocr_enabled: bool = Field(
        default=True,
        description="Register Surya OCR 2 in the benchmark document-model catalog.",
    )
    surya_inference_backend: str = Field(
        default="llamacpp",
        description=(
            "Surya inference backend (SURYA_INFERENCE_BACKEND). Repody uses llamacpp only."
        ),
    )
    surya_inference_url: str | None = Field(
        default=None,
        description=(
            "Pre-running llama-server OpenAI API base (SURYA_INFERENCE_URL), e.g. "
            "http://host:8001/v1. Required for Surya OCR in workers."
        ),
    )
    surya_inference_parallel: int = Field(
        default=8,
        ge=1,
        le=32,
        description=(
            "Client-side concurrency (SURYA_INFERENCE_PARALLEL). Match --parallel on llama-server."
        ),
    )
    surya_image_dpi: int = Field(
        default=96,
        ge=72,
        description=(
            "Surya IMAGE_DPI (datalab benchmark default). Also used when rasterizing PDF "
            "uploads to PNG before RecognitionPredictor."
        ),
    )
    surya_image_dpi_highres: int = Field(
        default=192,
        ge=72,
        description="Surya IMAGE_DPI_HIGHRES (datalab-to/surya settings.py default).",
    )
    surya_max_tokens_full_page: int = Field(
        default=12288,
        ge=1024,
        description="Surya SURYA_MAX_TOKENS_FULL_PAGE (datalab-to/surya settings.py default).",
    )
    surya_detector_text_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Surya DETECTOR_TEXT_THRESHOLD (datalab-to/surya settings.py default).",
    )
    surya_layout_block_ocr_enabled: bool = Field(
        default=False,
        description=(
            "Use LayoutPredictor + per-block RecognitionPredictor (datalab-to/surya block mode) "
            "instead of default full-page OCR."
        ),
    )
    surya_table_recognition_enabled: bool = Field(
        default=False,
        description=(
            "Run TableRecPredictor.predict_full on each page and append table HTML to benchmark text."
        ),
    )

    ocr_max_pages: int = Field(default=10, description="Max PDF pages per document.")
    ocr_max_pages_hard_cap: int = Field(default=50)
    document_render_max_edge_px: int = Field(
        default=896,
        description="Longest image edge when rasterizing documents for bundle cache.",
        validation_alias=AliasChoices("document_render_max_edge_px", "ocr_max_edge_px"),
    )
    document_render_pdf_dpi: int = Field(
        default=120,
        description="PDF rasterization DPI for bundle cache.",
        validation_alias=AliasChoices("document_render_pdf_dpi", "ocr_pdf_dpi"),
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

    stale_run_timeout_minutes: int = Field(default=3)
    queued_stale_timeout_minutes: int = Field(default=30)
    maintenance_interval_seconds: int = Field(default=60)
    dispatch_max_attempts: int = Field(
        default=8,
        ge=1,
        description="Max Hatchet dispatch attempts per run (outbox replay).",
    )

    operator_actions_enabled: bool = Field(default=False)
    operator_data_path: str = Field(default="/app/benchmark-reports")

    structured_llm_enabled: bool = Field(
        default=False,
        description="Use instructor/Pydantic for structured JSON when available.",
    )
    log_json: bool = Field(default=True)

    rate_limit_enabled: bool = Field(default=True)
    rate_limit_fail_closed: bool = Field(
        default=False,
        description="When true, reject run/http rate limits if Redis is unavailable (prod).",
    )
    rate_limit_window_seconds: int = Field(default=60)
    rate_limit_runs_per_workflow: int = Field(default=30)
    rate_limit_runs_per_client: int = Field(default=120)

    admission_control_enabled: bool = Field(
        default=True,
        description="Reject new runs when queue/inflight limits are exceeded.",
    )
    admission_max_queued: int = Field(
        default=80,
        description="Max runs waiting in queued status before HTTP 503.",
    )
    admission_max_inflight: int = Field(
        default=100,
        description="Max queued+running runs before HTTP 503.",
    )
    admission_max_ocr_inflight: int = Field(
        default=100,
        description="Max queued+running OCR/document-model runs before HTTP 503.",
    )
    admission_retry_after_seconds: int = Field(
        default=60,
        description="Retry-After header when admission rejects a run.",
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

    seed_on_startup: bool = False
    use_create_all: bool = Field(
        default=False,
        description="Create tables on startup (local tests only). Use Alembic in production.",
    )

    max_upload_bytes: int = Field(default=25 * 1024 * 1024)
    max_upload_files: int = Field(default=20)
    presigned_upload_ttl_seconds: int = Field(default=3600)
    direct_upload_enabled: bool = Field(default=True)
    upload_allowed_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/webp",
        ],
    )

    run_events_enabled: bool = Field(default=True)

    otel_enabled: bool = Field(default=False)
    otel_service_name: str = Field(default="repody-api")
    otel_exporter_endpoint: str = Field(default="http://localhost:4318/v1/traces")

    @model_validator(mode="after")
    def _sync_validation_options(self) -> Self:
        if self.llm_validation_enabled and not self.structured_llm_enabled:
            self.structured_llm_enabled = True
        if self.oidc_enabled and not self.oidc_issuer:
            raise ValueError("AUDIT_OIDC_ISSUER is required when AUDIT_OIDC_ENABLED=true.")
        if not self.vllm_api_key:
            self.vllm_api_key = os.getenv("AUDIT_VLLM_API_KEY", "").strip() or None
        from audit_workbench.inference.runtime import is_remote_vllm_url

        if self.inference_mode.lower() == "vllm" and is_remote_vllm_url(self.vllm_base_url):
            probe_env = os.getenv("AUDIT_GPU_LIVE_PROBE", "").strip().lower()
            health_env = os.getenv("AUDIT_HEALTHZ_PROBE_INFERENCE", "").strip().lower()
            if probe_env not in ("true", "1", "yes"):
                self.gpu_live_probe = False
            if health_env not in ("true", "1", "yes"):
                self.healthz_probe_inference = False
        elif os.getenv("AUDIT_GPU_LIVE_PROBE") is None:
            self.gpu_live_probe = True
        if self.use_create_all and "postgresql" in self.database_url.lower():
            import warnings

            warnings.warn(
                "AUDIT_USE_CREATE_ALL=true with PostgreSQL — prefer Alembic migrations in production.",
                stacklevel=1,
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
