"""Versioned cross-service and Hatchet orchestration contracts."""

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

CONTRACT_VERSION = "1.0"

ModuleSource = Literal["core", "idp", "fraud", "operator"]
ArtifactKind = Literal[
    "source_document",
    "pdf_revision_diff",
    "forensic_heatmap",
    "browser_screenshot",
    "playwright_trace",
    "json_report",
]
FraudSeverity = Literal["clean", "low", "medium", "high", "critical"]
FourEyesDecision = Literal["approved", "rejected", "returned_to_maker"]


class ArtifactRef(BaseModel):
    """Reference to an immutable object stored in S3."""

    artifact_id: str
    module: ModuleSource
    kind: ArtifactKind
    storage_key: str
    sha256: str
    mime_type: str
    byte_size: int = Field(ge=0)


class CaseRef(BaseModel):
    """Domain-agnostic unit of work orchestrated by ``repody-core``.

    Supports document cases, pure-JSON standalone Computer-Use payloads, and
    combined multi-module pipelines without hardwiring every case to documents.
    """

    contract_version: str = CONTRACT_VERSION
    case_id: str
    account_id: str | None = None
    external_ref: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class FraudFinding(BaseModel):
    """Explainable evidence finding produced by Fraud Shield."""

    detector: str
    tier: Literal[1, 2, 3]
    code: str
    severity: FraudSeverity
    title: str
    detail: str
    page: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None
    evidence_artifact_id: str | None = None


class FraudPreCheckInput(BaseModel):
    """Input to ``fraud.pre_check`` before expensive VLM extraction."""

    contract_version: str = CONTRACT_VERSION
    case: CaseRef
    artifacts: list[ArtifactRef]


class FraudPreCheckOutput(BaseModel):
    """Deterministic Tier-1 PDF, signature, and template-reuse result."""

    contract_version: str = CONTRACT_VERSION
    analysis_id: str
    risk_score: int = Field(ge=0, le=100)
    severity: FraudSeverity
    short_circuit_recommended: bool = False
    findings: list[FraudFinding] = Field(default_factory=list)
    generated_artifacts: list[ArtifactRef] = Field(default_factory=list)


class IdpStageInput(BaseModel):
    """Input to ``idp.extract_and_validate``."""

    contract_version: str = CONTRACT_VERSION
    case: CaseRef
    workflow_id: str
    artifacts: list[ArtifactRef]


class IdpStageOutput(BaseModel):
    """Structured extraction and rule-evaluation summary returned to core."""

    contract_version: str = CONTRACT_VERSION
    idp_run_id: str
    outcome: Literal["passed", "warning", "failed"]
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    flagged_fields: list[str] = Field(default_factory=list)
    pages_processed: int = Field(default=0, ge=0)


class FraudPostVerifyInput(BaseModel):
    """Input to ``fraud.post_verify`` (Tier-2 math/logic + Tier-3 visual localization)."""

    contract_version: str = CONTRACT_VERSION
    case: CaseRef
    artifacts: list[ArtifactRef]
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    pre_check_analysis_id: str | None = None


class FraudPostVerifyOutput(BaseModel):
    """Post-extraction verification and visual tampering localization output."""

    contract_version: str = CONTRACT_VERSION
    analysis_id: str
    risk_score: int = Field(ge=0, le=100)
    severity: FraudSeverity
    requires_four_eyes: bool
    findings: list[FraudFinding] = Field(default_factory=list)
    generated_artifacts: list[ArtifactRef] = Field(default_factory=list)


class FieldOverrideRecord(BaseModel):
    """Immutable audit record of a human field correction during Maker review."""

    field_path: str
    before_value: Any
    after_value: Any
    actor_sub: str
    reason: str = Field(min_length=1)
    created_at: datetime


class FourEyesApprovalEvent(BaseModel):
    """Signed Maker-Checker decision that resumes a paused Hatchet durable task."""

    contract_version: str = CONTRACT_VERSION
    approval_id: str
    case_id: str
    payload_sha256: str = Field(min_length=64, max_length=64)
    maker_sub: str = Field(min_length=1)
    checker_sub: str = Field(min_length=1)
    decision: FourEyesDecision
    note: str = ""
    decided_at: datetime

    @model_validator(mode="after")
    def _enforce_four_eyes(self) -> Self:
        if self.decision == "approved" and self.maker_sub == self.checker_sub:
            raise ValueError("Four-eyes violation: checker_sub must differ from maker_sub.")
        return self
