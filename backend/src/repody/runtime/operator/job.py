"""Operator job DTO — mutable job record + store serialization (platform)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class OperatorJob:
    id: str
    kind: str
    label: str
    status: str = "queued"
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: str = ""
    output: str = ""
    error: str | None = None
    report_path: str | None = None


def job_to_store(job: OperatorJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind,
        "label": job.label,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "progress": job.progress,
        "output": job.output,
        "error": job.error,
        "report_path": job.report_path,
    }


def job_from_store(payload: dict[str, Any]) -> OperatorJob:
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    return OperatorJob(
        id=str(payload["id"]),
        kind=str(payload["kind"]),
        label=str(payload["label"]),
        status=str(payload.get("status", "queued")),
        created_at=_parse_dt(payload.get("created_at")) or utc_now(),
        started_at=_parse_dt(payload.get("started_at")),
        completed_at=_parse_dt(payload.get("completed_at")),
        progress=str(payload.get("progress", "")),
        output=str(payload.get("output", "")),
        error=payload.get("error"),
        report_path=payload.get("report_path"),
    )


MAX_OUTPUT_CHARS = 24_000


def truncate_output(existing: str, text: str, *, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    return f"{existing}{text}"[-max_chars:]


def progress_from_chunk(text: str, *, max_chars: int = 300) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    return lines[-1][-max_chars:]
