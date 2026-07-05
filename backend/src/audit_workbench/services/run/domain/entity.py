from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class DomainRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


@dataclass
class RunEntity:
    """Enterprise entity for audit run lifecycle — no framework or persistence imports."""

    id: str
    workflow_id: str
    source: str
    status: DomainRunStatus
    worker_pool: str | None = None
    overall_status: str | None = None
    error: str | None = None
    summary_total: int = 0
    summary_passed: int = 0
    summary_failed: int = 0
    fields_extracted: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    run_metadata: dict[str, Any] | None = None
    progress: dict[str, Any] | None = None
