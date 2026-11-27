"""Stage contracts matching ``repody_common.contracts`` (version ``1.0``)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

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
    """Domain-agnostic unit of work orchestrated by ``repody-core``."""

    contract_version: str = CONTRACT_VERSION
    case_id: str
    account_id: str | None = None
    external_ref: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)


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
