"""Platform settings: every AUDIT_* environment variable, in one pydantic-settings model."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from repody.settings.validators import (
    validate_production_guardrails,
    validate_timeout_alignment,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUDIT_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Core: app, database, Redis, CORS, logging, tracing ---
    app_name: str = "Repody"
    debug: bool = False

    database_url: str = Field(default="postgresql+asyncpg://audit:audit@localhost:5432/repody")
    db_pool_size: int = Field(
        default=20,
        description=(
            "SQLAlchemy async pool size per process. "
            "API needs headroom for requests + maintenance; "
            "workers should be >= max_jobs + 2."
        ),
    )
    db_max_overflow: int = Field(
        default=20,
        description="Extra DB connections beyond pool_size.",
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Seconds to wait for a DB connection.",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(
        default=64,
        description="Shared Redis pool size (cache + SSE pub/sub).",
    )

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    deployment_environment: str = Field(
        default="development",
        description="Deployment label attached to logs and traces (e.g. production).",
    )
    run_migrations_on_startup: bool = Field(
        default=False,
        description="Run Alembic upgrade head before serving (Docker entrypoint).",
    )

    seed_on_startup: bool = False

    log_json: bool = Field(default=True)
    log_file: str | None = Field(
        default=None,
        description="Optional path for JSON log lines (Alloy → Loki in local dev).",
    )

    run_events_enabled: bool = Field(default=True)
    # --- Workers: Taskiq pools and task timeout ---
    worker_task_timeout_minutes: int = Field(
        default=3,
        ge=1,
        le=15,
        description=(
            "Max minutes for a Taskiq audit-run task before cancellation "
            "(hard ceiling 15; raise for long OCR PDFs alongside model timeouts)."
        ),
    )
    worker_pool: str = Field(
        default="extract",
        description="Active Taskiq pool for this worker process (extract|fast).",
    )
    worker_extract_max_jobs: int = Field(
        default=1,
        ge=1,
        description=(
            "Max concurrent extract pool tasks per worker process. Keep 1 when sharing "
            "a single GPU/VLM; raise only with per-replica GPU headroom and matching "
            "AUDIT_DB_POOL_SIZE (>= max_jobs + 2)."
        ),
    )
    worker_fast_max_jobs: int = Field(
        default=4,
        description="Max concurrent fast pool tasks per worker process.",
    )
    worker_pool_fast: str = Field(
        default="fast", description="Taskiq queue name suffix for fast IDP runs."
    )
    worker_pool_extract: str = Field(
        default="extract",
        description="Taskiq queue name suffix for document-model IDP runs.",
    )
    # --- Auth: Keycloak OIDC ---
    oidc_enabled: bool = Field(
        default=False,
        description="Require Keycloak JWT on management endpoints (disable for local pytest).",
    )
    oidc_issuer: str | None = Field(
        default=None,
        description="OIDC issuer URL, e.g. http://keycloak:8080/realms/repody",
    )
    oidc_issuer_aliases: str = Field(
        default="",
        description="Comma-separated or JSON list of extra accepted JWT issuers.",
    )
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

    def accepted_oidc_issuer_aliases(self) -> list[str]:
        return self._parse_oidc_issuer_aliases(self.oidc_issuer_aliases)

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

    # --- Storage: MinIO/S3 and upload limits ---
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
    # --- Inference: NuExtract on the llama-server, extraction cache ---
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
    # --- Ops: maintenance, rate limits, admission caps ---
    stale_run_timeout_minutes: int = Field(
        default=5,
        description="Fail running runs older than this (maintenance reap).",
    )
    queued_stale_timeout_minutes: int = Field(
        default=60,
        description="Fail queued runs when no workers are running and age exceeds this.",
    )
    maintenance_interval_seconds: int = Field(
        default=60,
    )

    rate_limit_enabled: bool = Field(default=True)
    rate_limit_fail_closed: bool = Field(
        default=False,
        description="When true, reject run/http rate limits if Redis is unavailable (prod).",
    )
    rate_limit_window_seconds: int = Field(default=60)
    rate_limit_runs_per_workflow: int = Field(
        default=300,
        description=(
            "Max run creates per workflow per window. "
            "Raise for high-RPS clients; admission caps are the hard capacity gate."
        ),
    )
    rate_limit_runs_per_client: int = Field(
        default=2000,
        description="Max run creates per client (API key/IP) per window.",
    )
    rate_limit_http_per_minute: int = Field(
        default=6000,
        ge=1,
        description=(
            "Global per-IP limit for mutating HTTP methods only "
            "(GET browse/poll is excluded so UI refresh does not burn the budget)."
        ),
    )

    queue_refresh_sse_limit: int = Field(
        default=32,
        ge=0,
        description=(
            "On maintenance queue refresh, publish SSE for at most this many "
            "queued runs (0 = DB-only, no SSE). Claim path does not fan out."
        ),
    )
    queue_refresh_db_limit: int = Field(
        default=128,
        ge=0,
        description=(
            "Max queued rows loaded/updated per maintenance tick "
            "(0 disables maintenance queue refresh)."
        ),
    )

    admission_max_queued: int = Field(
        default=200,
        ge=0,
        description="Reject enqueue with 503 when queued runs >= this (0 disables).",
    )
    admission_max_inflight: int = Field(
        default=100,
        ge=0,
        description="Reject enqueue when queued+running >= this (0 disables).",
    )
    admission_max_extract_inflight: int = Field(
        default=20,
        ge=0,
        description=(
            "Reject extract-pool enqueue when extract inflight >= this (0 disables). "
            "Protects shared VLM capacity."
        ),
    )
    admission_retry_after_seconds: int = Field(
        default=15,
        ge=1,
        description="Retry-After hint when admission returns CAPACITY.",
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.oidc_enabled and not self.oidc_issuer:
            raise ValueError("AUDIT_OIDC_ISSUER is required when AUDIT_OIDC_ENABLED=true.")
        validate_production_guardrails(self)
        validate_timeout_alignment(self)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
