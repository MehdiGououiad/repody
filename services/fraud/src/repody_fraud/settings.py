"""Environment settings for ``repody-fraud`` (``FRAUD_*``)."""

from functools import lru_cache

from pydantic import NonNegativeInt, PositiveFloat, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class FraudSettings(BaseSettings):
    """Configuration for Fraud Shield REST API and CPU/GPU Hatchet workers."""

    model_config = SettingsConfigDict(
        env_prefix="FRAUD_",
        env_file=".env",
        extra="ignore",
    )

    deployment_environment: str = "development"
    database_url: SecretStr = SecretStr("postgresql+asyncpg://localhost:5432/repody_fraud")
    db_pool_size: PositiveInt = 10
    health_timeout_seconds: PositiveFloat = 2.0

    # Object storage (SeaweedFS / S3)
    s3_endpoint_url: str = "http://localhost:8333"
    s3_region: str = "us-east-1"
    s3_access_key: str = "repody"
    s3_secret_key: SecretStr = SecretStr("")
    s3_bucket: str = "fraud-artifacts"

    # Auth (Keycloak OIDC)
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None

    # Hatchet worker routing (`fraud-cpu`, `fraud-gpu`, or `all`)
    hatchet_enabled: bool = False
    worker_pool: str = "all"
    worker_concurrency: PositiveInt = 4

    # Forensics thresholds
    max_upload_bytes: PositiveInt = 25 * 1024 * 1024
    max_pages_to_analyze: PositiveInt = 10
    phash_max_hamming_distance: NonNegativeInt = 6
    short_circuit_score_threshold: NonNegativeInt = 80
    four_eyes_score_threshold: NonNegativeInt = 40

    # Optional ONNX neural detector (MIT Mesorch / IML-ViT) — air-gap safe local path
    neural_model_path: str | None = None

    # Optional VLM hotspot explanation endpoint (Qwen3-VL Apache-2.0 via vLLM)
    explainer_base_url: str | None = None
    explainer_api_key: SecretStr | None = None
    explainer_model: str = "Qwen/Qwen3-VL-8B-Instruct"


@lru_cache
def get_settings() -> FraudSettings:
    """Return cached Fraud Shield settings."""
    return FraudSettings()
