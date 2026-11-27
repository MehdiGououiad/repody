"""Four-Eyes (Maker-Checker) approval schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from repody_common.contracts import FourEyesDecision

ApprovalStatus = Literal[
    "waiting_maker",
    "waiting_checker",
    "approved",
    "rejected",
    "returned_to_maker",
]


class FieldOverrideInput(BaseModel):
    """Human field correction proposed during Maker review."""

    field_path: str = Field(min_length=1)
    after_value: Any
    reason: str = Field(min_length=1)


class CreateApprovalRequest(BaseModel):
    """Open a Four-Eyes approval checkpoint for a case."""

    case_id: str = Field(min_length=1)
    stage_name: str = Field(min_length=1)
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)


class MakerSubmitRequest(BaseModel):
    """Maker review submission (with optional audited field overrides)."""

    overrides: list[FieldOverrideInput] = Field(default_factory=list)
    note: str = ""


class CheckerDecisionRequest(BaseModel):
    """Independent Checker decision (must be a distinct actor from Maker)."""

    decision: FourEyesDecision
    note: str = ""


class FieldOverrideResponse(BaseModel):
    """Immutable record of a human field edit."""

    id: str
    case_id: str
    approval_task_id: str
    field_path: str
    before_value: Any
    after_value: Any
    actor_sub: str
    reason: str
    created_at: datetime


class ApprovalTaskResponse(BaseModel):
    """Persisted Four-Eyes approval task state."""

    id: str
    case_id: str
    stage_name: str
    status: ApprovalStatus
    payload_snapshot: dict[str, Any]
    payload_sha256: str
    maker_sub: str | None
    maker_note: str
    maker_decided_at: datetime | None
    checker_sub: str | None
    checker_note: str
    checker_decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    overrides: list[FieldOverrideResponse] = Field(default_factory=list)
