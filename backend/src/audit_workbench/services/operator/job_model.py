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

    def to_store(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "output": self.output,
            "error": self.error,
            "report_path": self.report_path,
        }

    @classmethod
    def from_store(cls, payload: dict[str, Any]) -> OperatorJob:
        def _parse_dt(value: str | None) -> datetime | None:
            if not value:
                return None
            return datetime.fromisoformat(value)

        return cls(
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


def operator_job_schema(job: OperatorJob):
    from audit_workbench.schemas.operator import OperatorJobSchema

    return OperatorJobSchema(
        id=job.id,
        kind=job.kind,
        label=job.label,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress=job.progress,
        output=job.output,
        error=job.error,
        has_report=bool(job.report_path),
    )
