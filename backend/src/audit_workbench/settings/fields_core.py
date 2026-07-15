from __future__ import annotations

from pydantic import Field


class CoreSettingsFields:
    app_name: str = "Repody"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://audit:audit@localhost:5432/audit_workbench"
    )
    db_pool_size: int = Field(
        default=5,
        description="SQLAlchemy async pool size per process.",
    )
    db_max_overflow: int = Field(
        default=10,
        description="Extra DB connections beyond pool_size.",
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Seconds to wait for a DB connection.",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(
        default=20,
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
        description="Optional path for JSON log lines (Promtail → Loki in local dev).",
    )

    otel_enabled: bool = Field(default=False)
    otel_service_name: str = Field(default="repody-api")
    otel_exporter_endpoint: str = Field(default="http://localhost:4318/v1/traces")

    run_events_enabled: bool = Field(default=True)
