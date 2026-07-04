from __future__ import annotations

import enum


class WorkflowStatus(str, enum.Enum):
    active = "active"
    draft = "draft"
    paused = "paused"
    archived = "archived"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class OverallStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"
