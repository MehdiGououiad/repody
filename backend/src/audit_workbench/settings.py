from __future__ import annotations

import os
from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUDIT_", env_file=".env", extra="ignore")

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
        description="TLS strategy for Hatchet gRPC (none for hatchet-lite).",
    )
    hatchet_task_timeout_minutes: int = Field(
        default=3,
        description="Max minutes for a Hatchet audit-run task before cancellation.",
    )
    worker_pool_fast: str = Field(default="fast", description="Hatchet worker label for fast runs.")
    worker_pool_ocr: str = Field(default="ocr", description="Hatchet worker label for OCR runs.")

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    auth_enabled: bool = Field(
        default=False,
        description="Require AUDIT_ADMIN_API_TOKEN on management endpoints.",
    )
    admin_api_token: str | None = Field(
        default=None,
        description="Bearer token for UI/admin API access. Required when auth_enabled=true.",
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
            "Browser-reachable MinIO host:port for presigned upload URLs "
            "(e.g. localhost:9000)."
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
        default="agentcontrol/repody-vlm:q4_k_m-16k",
        description="Repody VLM model id in Docker Model Runner.",
    )
    repody_vlm_max_tokens: int = Field(default=512, ge=64)
    repody_vlm_max_edge_px: int = Field(default=1280, ge=512)
    repody_vlm_pdf_dpi: int = Field(default=144, ge=72)
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
        default=4,
        ge=1,
        description=(
            "Max rendered pages sent in one Repody VLM request. "
            "Cap pages to stay within model context."
        ),
    )

    ocr_max_pages: int = Field(default=10, description="Max PDF pages per document.")
    ocr_max_pages_hard_cap: int = Field(default=50)
    ocr_max_edge_px: int = Field(default=896, description="Default longest image edge for rendering.")
    ocr_pdf_dpi: int = Field(default=120)
    ocr_jpeg_quality: int = 82

    llm_validation_enabled: bool = Field(
        default=False,
        description="Enable LLM rule validation (requires validation_model in Docker Model Runner).",
    )
    validation_model: str | None = Field(
        default=None,
        description=(
            "Docker Model Runner text model id for LLM rule validation "
            "(e.g. agentcontrol/validation:q4_k_m-4k). Required when LLM validation is enabled."
        ),
    )
    validation_max_tokens: int = Field(default=128, ge=32)
    validation_timeout_seconds: float = Field(default=60.0, ge=5.0)

    extraction_cache_enabled: bool = True
    extraction_cache_ttl_seconds: int = 86400

    run_jobs_inline: bool = Field(
        default=False,
        description="Execute runs in-process (no Hatchet). Set true for local dev without workers.",
    )
    stale_run_timeout_minutes: int = Field(default=3)
    queued_stale_timeout_minutes: int = Field(default=30)
    maintenance_interval_seconds: int = Field(default=60)

    operator_actions_enabled: bool = Field(default=False)
    operator_data_path: str = Field(default="/app/benchmark-reports")

    structured_llm_enabled: bool = Field(
        default=False,
        description="Use instructor/Pydantic for structured JSON when available.",
    )
    log_json: bool = Field(default=True)

    rate_limit_enabled: bool = Field(default=True)
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

    parallel_doc_extraction: bool = True
    parallel_storage_fetch: bool = True
    progress_commit_interval_ms: int = Field(default=400)

    seed_on_startup: bool = False
    use_create_all: bool = Field(
        default=True,
        description="Create tables on startup (dev only). Use Alembic in production.",
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
    otel_service_name: str = Field(default="audit-workbench-api")
    otel_exporter_endpoint: str = Field(default="http://localhost:4318/v1/traces")

    @model_validator(mode="after")
    def _sync_validation_options(self) -> Self:
        if self.llm_validation_enabled and not self.structured_llm_enabled:
            self.structured_llm_enabled = True
        if self.auth_enabled and not self.admin_api_token:
            raise ValueError(
                "AUDIT_ADMIN_API_TOKEN is required when AUDIT_AUTH_ENABLED=true."
            )
        if not self.vllm_api_key:
            self.vllm_api_key = os.getenv("AUDIT_VLLM_API_KEY", "").strip() or None
        from audit_workbench.inference.runtime import is_remote_vllm_url

        if (
            self.inference_mode.lower() == "vllm"
            and is_remote_vllm_url(self.vllm_base_url)
        ):
            probe_env = os.getenv("AUDIT_GPU_LIVE_PROBE", "").strip().lower()
            health_env = os.getenv("AUDIT_HEALTHZ_PROBE_INFERENCE", "").strip().lower()
            if probe_env not in ("true", "1", "yes"):
                self.gpu_live_probe = False
            if health_env not in ("true", "1", "yes"):
                self.healthz_probe_inference = False
        elif os.getenv("AUDIT_GPU_LIVE_PROBE") is None:
            self.gpu_live_probe = True
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
