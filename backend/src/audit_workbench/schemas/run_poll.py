from __future__ import annotations

from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import RunAuditDetail, RunProgressSchema


class RunPollStatus(CamelModel):
    status: str
    progress: RunProgressSchema | None = None
    error: str | None = None


class RunPollBody(CamelModel):
    status: str
    progress: RunProgressSchema | None = None
    result: RunAuditDetail | None = None
    error: str | None = None
