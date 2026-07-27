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

    agent_idp_enabled: bool = Field(
        default=True,
        description="When false, IDP is omitted from the platform agent recipe.",
    )
    agent_fraud_enabled: bool = Field(
        default=False,
        description="When true, Fraud may run after IDP when included in the recipe.",
    )
    agent_fraud_workers_ready: bool = Field(
        default=False,
        description=(
            "When true with agent_fraud_enabled, Fraud is dispatchable. "
            "Keep false until worker-fraud Deployment has replicas > 0."
        ),
    )
    agent_computer_use_enabled: bool = Field(
        default=False,
        description="When true, Computer Use may run after prior agents when included in the recipe.",
    )
    agent_computer_use_workers_ready: bool = Field(
        default=False,
        description=(
            "When true with agent_computer_use_enabled, Computer Use is dispatchable. "
            "Keep false until worker-computer-use Deployment has replicas > 0."
        ),
    )
