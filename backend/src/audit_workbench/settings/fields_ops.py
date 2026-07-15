from __future__ import annotations

from pydantic import Field


class OpsSettingsFields:
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
    dispatch_max_attempts: int = Field(
        default=8,
        ge=1,
        description="Max Taskiq dispatch attempts per run (outbox replay).",
    )

    operator_actions_enabled: bool = Field(default=False)
    operator_data_path: str = Field(default="/app/benchmark-reports")

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
        default=50,
        description="Max runs waiting in queued status before HTTP 503.",
    )
    admission_max_inflight: int = Field(
        default=64,
        description="Max queued+running runs before HTTP 503.",
    )
    admission_max_extract_inflight: int = Field(
        default=8,
        description="Max queued+running document-model runs before HTTP 503.",
    )
    admission_retry_after_seconds: int = Field(
        default=60,
        description="Retry-After header when admission rejects a run.",
    )
