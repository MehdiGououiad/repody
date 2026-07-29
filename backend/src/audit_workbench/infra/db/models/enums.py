from __future__ import annotations

import enum

from audit_workbench.runtime.run.status import RunStatus

__all__ = ["OverallStatus", "RunStatus", "WorkflowStatus"]


class WorkflowStatus(str, enum.Enum):
    active = "active"
    draft = "draft"
    paused = "paused"
    archived = "archived"


class OverallStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"
