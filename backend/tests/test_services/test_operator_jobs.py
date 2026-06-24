from __future__ import annotations

from datetime import UTC, datetime

from audit_workbench.services.operator_job_model import OperatorJob


def test_operator_job_store_round_trip_preserves_public_state() -> None:
    job = OperatorJob(
        id="job-1",
        kind="benchmark",
        label="Models benchmark",
        status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        started_at=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, 0, 2, tzinfo=UTC),
        progress="done",
        output="all good",
        report_path="/tmp/report.json",
    )

    restored = OperatorJob.from_store(job.to_store())

    assert restored == job
    assert restored.as_dict()["hasReport"] is True
    assert restored.as_dict()["startedAt"] == "2026-01-01T00:01:00+00:00"
