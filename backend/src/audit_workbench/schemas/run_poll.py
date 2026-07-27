"""Run poll DTOs — body aliases workflow OpenAPI model (single source of truth)."""

from __future__ import annotations

from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import RunPollResponse as RunPollBody
from audit_workbench.schemas.workflow import RunProgressSchema

__all__ = ["RunPollBody", "RunPollStatus", "RunProgressSchema"]


class RunPollStatus(CamelModel):
    status: str
    progress: RunProgressSchema | None = None
    error: str | None = None
