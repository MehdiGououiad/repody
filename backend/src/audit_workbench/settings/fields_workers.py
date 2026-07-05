from __future__ import annotations

from pydantic import AliasChoices, Field


class WorkerSettingsFields:
    worker_task_timeout_minutes: int = Field(
        default=3,
        ge=1,
        le=3,
        validation_alias=AliasChoices("AUDIT_WORKER_TASK_TIMEOUT_MINUTES"),
        description="Max minutes for a Taskiq audit-run task before cancellation (hard cap: 3).",
    )
    worker_pool: str = Field(
        default="extract",
        validation_alias=AliasChoices("AUDIT_WORKER_POOL"),
        description="Active Taskiq pool for this worker process (extract | fast).",
    )
    worker_extract_max_jobs: int = Field(
        default=1,
        validation_alias=AliasChoices("AUDIT_WORKER_EXTRACT_MAX_JOBS", "AUDIT_WORKER_SLOTS"),
        description="Max concurrent extract pool tasks per worker process.",
    )
    worker_fast_max_jobs: int = Field(
        default=4,
        validation_alias=AliasChoices("AUDIT_WORKER_FAST_MAX_JOBS", "AUDIT_WORKER_SLOTS"),
        description="Max concurrent fast pool tasks per worker process.",
    )
    worker_pool_fast: str = Field(default="fast", description="Taskiq queue name suffix for fast runs.")
    worker_pool_extract: str = Field(
        default="extract",
        description="Taskiq queue name suffix for document-model extraction runs.",
    )
