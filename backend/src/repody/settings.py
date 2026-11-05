"""Every AUDIT_* environment variable, in one pydantic-settings model."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# A comma-separated env value (pydantic-settings' NoDecode recipe).
CommaList = Annotated[
    list[str],
    NoDecode,
    BeforeValidator(
        lambda v: [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else v
    ),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUDIT_", env_file=".env", extra="ignore")

    # Platform
    deployment_environment: str = "development"
    debug: bool = False
    log_json: bool = True
    cors_origins: CommaList = ["http://localhost:3000"]
    seed_on_startup: bool = False

    # Postgres, Redis, S3
    database_url: str = "postgresql+asyncpg://audit:audit@localhost:5432/repody"
    db_pool_size: int = 10
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "audit-documents"

    # Auth (Keycloak). Issuer aliases cover the same realm reached by another host name.
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_issuer_aliases: CommaList = []
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None

    # Uploads
    max_upload_bytes: int = 25 * 1024 * 1024
    max_upload_files: int = 20
    upload_allowed_mime_types: CommaList = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    ]

    # Inference: NuExtract on an OpenAI-compatible llama-server
    llamacpp_base_url: str = "http://127.0.0.1:8081/v1"
    llamacpp_api_key: str = "local"
    llamacpp_served_model: str = "nuextract3-q4_k_m"
    inference_timeout_seconds: float = Field(default=180.0, ge=10)

    # Markdown transcription (documents without fields): NuExtract's markdown mode, or
    # LightOnOCR-3 on its own OpenAI-compatible server (llama-server or vLLM).
    markdown_provider: Literal["nuextract", "lightonocr"] = "nuextract"
    lightonocr_base_url: str = "http://127.0.0.1:8082/v1"
    lightonocr_api_key: str = "local"
    lightonocr_served_model: str = "lightonocr-3-4b"
    max_pages_per_document: int | None = Field(default=None, ge=1)
    extraction_cache_ttl_seconds: int = 0  # 0 disables the Redis extraction cache

    # Runs
    run_timeout_minutes: int = Field(default=5, ge=1)
    max_queued_runs: int = 200  # enqueue answers 503 beyond this (0 disables)
    runs_per_minute_per_client: int = 600  # per API key or IP (0 disables)
    maintenance_interval_seconds: int = 60

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.oidc_enabled and not self.oidc_issuer:
            raise ValueError("AUDIT_OIDC_ISSUER is required when AUDIT_OIDC_ENABLED=true.")
        if self.deployment_environment == "production" and not self.oidc_enabled:
            raise ValueError("AUDIT_OIDC_ENABLED must be true in production.")
        if self.inference_timeout_seconds > self.run_timeout_minutes * 60:
            raise ValueError("AUDIT_INFERENCE_TIMEOUT_SECONDS must fit in the run timeout.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
