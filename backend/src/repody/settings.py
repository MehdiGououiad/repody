"""Every AUDIT_* environment variable, in one pydantic-settings model.

Secrets are ``SecretStr``: they never appear in a repr, a log line or an error report (Sentry
serialises local variables); code reads them with ``get_secret_value()`` where it connects.
"""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import (
    BeforeValidator,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    SecretStr,
    model_validator,
)
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
    # Origins of browser apps that call the API directly (the web app goes through its own
    # server, same origin). Requests carry a bearer token, never cookies.
    cors_origins: CommaList = []
    seed_on_startup: bool = False

    # Postgres, Redis, S3 (Compose: SeaweedFS)
    database_url: SecretStr = SecretStr("postgresql+asyncpg://audit:audit@localhost:5432/repody")
    db_pool_size: PositiveInt = 10
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    s3_endpoint_url: str = "http://localhost:8333"
    s3_region: str = "us-east-1"
    s3_access_key: str = "repody"
    s3_secret_key: SecretStr = SecretStr("s3-local-dev")
    s3_bucket: str = "audit-documents"

    # Auth (Keycloak). Issuer aliases cover the same realm reached by another host name.
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_issuer_aliases: CommaList = []
    # The access tokens' `aud` (Keycloak: an audience mapper on the web client). Required in
    # production, so a token issued to another client of the realm is not accepted.
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None

    # Uploads
    max_upload_bytes: PositiveInt = 25 * 1024 * 1024
    max_upload_files: PositiveInt = 20
    upload_allowed_mime_types: CommaList = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    ]

    # Inference: NuExtract on an OpenAI-compatible llama-server
    llamacpp_base_url: str = "http://127.0.0.1:8081/v1"
    llamacpp_api_key: SecretStr = SecretStr("local")
    llamacpp_served_model: str = "nuextract3-q8_0"
    inference_timeout_seconds: float = Field(default=180.0, ge=10)
    # Requests in flight per model server: set to its parallel slots (llama-server --parallel).
    # Documents and pages beyond it wait their turn.
    inference_concurrency: PositiveInt = 1

    # Markdown transcription (documents without fields): NuExtract's markdown mode, or
    # LightOnOCR-3 on its own OpenAI-compatible server (llama-server or vLLM).
    markdown_provider: Literal["nuextract", "lightonocr"] = "nuextract"
    lightonocr_base_url: str = "http://127.0.0.1:8082/v1"
    lightonocr_api_key: SecretStr = SecretStr("local")
    lightonocr_served_model: str = "lightonocr-3-4b"
    max_pages_per_document: PositiveInt | None = None
    extraction_cache_ttl_seconds: NonNegativeInt = 0  # 0 disables the Redis extraction cache

    # Runs
    run_timeout_minutes: PositiveInt = 5
    max_queued_runs: NonNegativeInt = 200  # enqueue answers 503 beyond this (0 disables)
    # Per workflow API key or signed-in user (0 disables).
    runs_per_minute_per_client: NonNegativeInt = 600
    maintenance_interval_seconds: PositiveInt = 60
    # Finished runs (and their uploaded files) older than this are deleted; 0 keeps them.
    run_retention_days: NonNegativeInt = 0
    # Health probes give up after this long (a hung Postgres or Redis reads as down).
    health_timeout_seconds: PositiveFloat = 2.0

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.oidc_enabled and not self.oidc_issuer:
            raise ValueError("AUDIT_OIDC_ISSUER is required when AUDIT_OIDC_ENABLED=true.")
        if self.deployment_environment == "production":
            if not self.oidc_enabled:
                raise ValueError("AUDIT_OIDC_ENABLED must be true in production.")
            if not self.oidc_audience:
                raise ValueError("AUDIT_OIDC_AUDIENCE is required in production.")
        if self.inference_timeout_seconds > self.run_timeout_minutes * 60:
            raise ValueError("AUDIT_INFERENCE_TIMEOUT_SECONDS must fit in the run timeout.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
