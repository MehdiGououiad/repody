"""Typed multi-module pipeline schemas and Hatchet orchestration inputs."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from repody_common.contracts import CaseRef
from repody_core.schemas.cases import PipelineStatus


class IdpPipelineStage(BaseModel):
    """Run an IDP extraction and validation workflow."""

    kind: Literal["idp"] = "idp"
    workflow_id: str = Field(min_length=1)


class FraudPreCheckStage(BaseModel):
    """Run deterministic pre-extraction Fraud Shield checks."""

    kind: Literal["fraud_pre_check"] = "fraud_pre_check"
    short_circuit_on_critical: bool = True


class FraudPostVerifyStage(BaseModel):
    """Run post-extraction Fraud Shield logic and visual localization."""

    kind: Literal["fraud_post_verify"] = "fraud_post_verify"


class FourEyesGateStage(BaseModel):
    """Pause the durable pipeline until Checker approval resolves."""

    kind: Literal["four_eyes_gate"] = "four_eyes_gate"
    approval_id: str | None = None
    stage_name: str = "four_eyes_gate"


PipelineStage = Annotated[
    IdpPipelineStage | FraudPreCheckStage | FraudPostVerifyStage | FourEyesGateStage,
    Field(discriminator="kind"),
]


class StartPipelineRequest(BaseModel):
    """Start a durable multi-module pipeline for an existing case."""

    stages: list[PipelineStage] = Field(min_length=1)


class PipelineRunResponse(BaseModel):
    """Persisted pipeline execution state."""

    id: str
    case_id: str
    stages: list[dict[str, Any]]
    status: PipelineStatus
    hatchet_run_id: str | None
    created_at: datetime
    finished_at: datetime | None


class PipelineTaskInput(BaseModel):
    """Input payload for the durable ``pipeline-execute`` Hatchet workflow."""

    pipeline_run_id: str | None = None
    case: CaseRef
    stages: list[PipelineStage] = Field(default_factory=list)
    approval_id: str | None = None
