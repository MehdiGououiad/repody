from __future__ import annotations

from datetime import UTC, datetime

from audit_workbench.infra.db.models import Run
from audit_workbench.infra.db.models.enums import RunStatus
from audit_workbench.app.run.persistence import (
    apply_entity_to_orm,
    entity_from_orm,
)
from audit_workbench.app.run.lifecycle import RunStatus
from audit_workbench.app.run.lifecycle import start_field_updates


def test_entity_from_orm_round_trip() -> None:
    run = Run(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=RunStatus.running.value,
        summary_total=3,
        error="oops",
    )
    entity = entity_from_orm(run)
    assert entity.id == "run-1"
    assert entity.status == RunStatus.running
    assert entity.summary_total == 3
    assert entity.error == "oops"

    entity.status = RunStatus.failed
    entity.error = "fixed"
    apply_entity_to_orm(entity, run)
    assert run.status == RunStatus.failed.value
    assert run.error == "fixed"


def test_start_field_updates_map_to_orm_values() -> None:
    now = datetime.now(UTC)
    updates = start_field_updates(now)
    from dataclasses import asdict

    values = asdict(updates)
    values["status"] = updates.status.value
    assert values["status"] == "running"
    assert values["started_at"] == now
    assert values["last_activity_at"] == now
    assert values["summary_total"] == 0
