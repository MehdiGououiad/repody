"""Environment settings for ``repody-core`` (``REPODY_CORE_*``)."""

from functools import lru_cache

from pydantic import PositiveFloat, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Configuration for the core API and durable Hatchet orchestrator."""

    model_config = SettingsConfigDict(
        env_prefix="REPODY_CORE_",
        env_file=".env",
        extra="ignore",
    )

    deployment_environment: str = "development"
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://repody:repody@localhost:5432/repody_core"
    )
    db_pool_size: PositiveInt = 10
    health_timeout_seconds: PositiveFloat = 2.0

    # Auth (Keycloak OIDC)
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None

    # Offline Ed25519 license
    license_token: SecretStr | None = None
    license_public_key_pem: str | None = None

    # Hatchet orchestration
    hatchet_enabled: bool = False
    worker_concurrency: PositiveInt = 8
    approval_sla_hours: PositiveInt = 72


@lru_cache
def get_settings() -> CoreSettings:
    """Return cached settings."""
    return CoreSettings()
