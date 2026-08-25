from __future__ import annotations

from pydantic import Field


class WorkerSettingsFields:
    worker_task_timeout_minutes: int = Field(
        default=3,
        ge=1,
        le=15,
        description=(
            "Max minutes for a Taskiq audit-run task before cancellation "
            "(hard ceiling 15; raise for long OCR PDFs alongside model timeouts)."
        ),
    )
    worker_pool: str = Field(
        default="extract",
        description="Active Taskiq pool for this worker process (extract|fast|fraud|computer_use).",
    )
    worker_extract_max_jobs: int = Field(
        default=1,
        ge=1,
        description=(
            "Max concurrent extract pool tasks per worker process. Keep 1 when sharing "
            "a single GPU/VLM; raise only with per-replica GPU headroom and matching "
            "AUDIT_DB_POOL_SIZE (>= max_jobs + 2)."
        ),
    )
    worker_fast_max_jobs: int = Field(
        default=4,
        description="Max concurrent fast pool tasks per worker process.",
    )
    worker_fraud_max_jobs: int = Field(
        default=4,
        description="Reserved fraud pool concurrency (Helm worker at replicas 0).",
    )
    worker_computer_use_max_jobs: int = Field(
        default=2,
        description="Reserved computer_use pool concurrency (Helm worker at replicas 0).",
    )
    worker_pool_fast: str = Field(
        default="fast", description="Taskiq queue name suffix for fast IDP runs."
    )
    worker_pool_extract: str = Field(
        default="extract",
        description="Taskiq queue name suffix for document-model IDP runs.",
    )
    worker_pool_fraud: str = Field(
        default="fraud",
        description="Reserved Taskiq queue suffix (no producer/API broker until agent ships).",
    )
    worker_pool_computer_use: str = Field(
        default="computer_use",
        description="Reserved Taskiq queue suffix (no producer/API broker until agent ships).",
    )
