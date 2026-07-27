from __future__ import annotations

from pydantic import Field


class WorkerSettingsFields:
    worker_task_timeout_minutes: int = Field(
        default=3,
        ge=1,
        le=3,
        description="Max minutes for a Taskiq audit-run task before cancellation (hard cap: 3).",
    )
    worker_pool: str = Field(
        default="extract",
        description="Active Taskiq pool for this worker process (extract|fast|fraud|computer_use).",
    )
    worker_extract_max_jobs: int = Field(
        default=1,
        description="Max concurrent extract pool tasks per worker process.",
    )
    worker_fast_max_jobs: int = Field(
        default=4,
        description="Max concurrent fast pool tasks per worker process.",
    )
    worker_fraud_max_jobs: int = Field(
        default=4,
        description="Max concurrent fraud pool tasks per worker process.",
    )
    worker_computer_use_max_jobs: int = Field(
        default=2,
        description="Max concurrent computer_use pool tasks per worker process.",
    )
    worker_pool_fast: str = Field(default="fast", description="Taskiq queue name suffix for fast IDP runs.")
    worker_pool_extract: str = Field(
        default="extract",
        description="Taskiq queue name suffix for document-model IDP runs.",
    )
    worker_pool_fraud: str = Field(
        default="fraud",
        description="Taskiq queue name suffix for fraud agent stages.",
    )
    worker_pool_computer_use: str = Field(
        default="computer_use",
        description="Taskiq queue name suffix for computer-use agent stages.",
    )
