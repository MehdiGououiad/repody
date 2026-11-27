"""Case and pipeline schemas (domain-agnostic: supports zero-document jobs)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from repody_common.contracts import ArtifactKind, ModuleSource

CaseStatus = Literal[
    "open",
    "in_progress",
    "waiting_maker",
    "waiting_checker",
    "approved",
    "rejected",
    "failed",
]

PipelineStatus = Literal[
    "queued",
    "running",
    "waiting_approval",
    "done",
    "rejected",
    "failed",
]


class ArtifactCreate(BaseModel):
    """Metadata for attaching an artifact reference to a case."""

    module: ModuleSource = "core"
    kind: ArtifactKind = "source_document"
    storage_key: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    mime_type: str = Field(min_length=1)
    byte_size: int = Field(ge=0)


class ArtifactResponse(ArtifactCreate):
    """Persisted artifact metadata."""

    id: str
    case_id: str
    created_at: datetime


class CreateCaseRequest(BaseModel):
    """Create a domain-agnostic case (artifacts, JSON input_payload, or both)."""

    account_id: str | None = None
    external_ref: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactCreate] = Field(default_factory=list)


class CaseResponse(BaseModel):
    """Case summary and current lifecycle state."""

    id: str
    account_id: str | None
    external_ref: str | None
    input_payload: dict[str, Any]
    status: CaseStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
