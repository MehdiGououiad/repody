from __future__ import annotations

from pydantic import AliasChoices, Field


class WorkerSettingsFields:
    worker_task_timeout_minutes: int = Field(
        default=3,
        validation_alias=AliasChoices("AUDIT_WORKER_TASK_TIMEOUT_MINUTES"),
        description="Max minutes for a Taskiq audit-run task before cancellation.",
    )
    worker_pool: str = Field(
        default="ocr",
        validation_alias=AliasChoices("AUDIT_WORKER_POOL"),
        description="Active Taskiq pool for this worker process (ocr | fast).",
    )
    worker_ocr_max_jobs: int = Field(
        default=1,
        validation_alias=AliasChoices("AUDIT_WORKER_OCR_MAX_JOBS", "AUDIT_WORKER_SLOTS"),
        description="Max concurrent OCR pool tasks per worker process.",
    )
    worker_fast_max_jobs: int = Field(
        default=4,
        validation_alias=AliasChoices("AUDIT_WORKER_FAST_MAX_JOBS", "AUDIT_WORKER_SLOTS"),
        description="Max concurrent fast pool tasks per worker process.",
    )
    worker_pool_fast: str = Field(default="fast", description="Taskiq queue name suffix for fast runs.")
    worker_pool_ocr: str = Field(default="ocr", description="Taskiq queue name suffix for OCR runs.")
