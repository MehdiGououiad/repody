"""Schema constraint and Hatchet workflow definition tests."""

from sqlalchemy import CheckConstraint

from repody_core.infra import models


def test_approval_task_enforces_four_eyes_check_constraint() -> None:
    table = models.Base.metadata.tables["approval_tasks"]
    constraints = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    names = {c.name for c in constraints}
    assert "ck_approval_tasks_four_eyes_distinct_actors" in names


def test_core_tables_exist_without_idp_coupling() -> None:
    table_names = set(models.Base.metadata.tables)
    assert {
        "cases",
        "artifacts",
        "pipeline_runs",
        "approval_tasks",
        "field_overrides",
        "audit_events",
        "usage_entries",
    }.issubset(table_names)
    assert "documents" not in table_names
    assert "workflows" not in table_names
