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
