from __future__ import annotations

from pydantic import BaseModel, Field


class AuditRunInput(BaseModel):
    run_id: str = Field(description="Primary key of the audit run row.")
    extract_pool: str = Field(default="extract", description="Worker pool (extract|fast).")
    workflow_id: str | None = Field(default=None, description="Workflow that owns the run.")
    request_id: str | None = Field(
        default=None,
        description="HTTP correlation / request id from the API enqueue call.",
    )
