"""Domain schemas for Fraud Shield analyses, evidence artifacts, and fingerprints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from repody_common.contracts import ArtifactKind, ArtifactRef, FraudFinding, FraudSeverity

AnalysisMode = Literal["standalone", "pre_check", "post_verify"]


class GeneratedEvidence(BaseModel):
    """In-memory visual evidence image emitted by a pure forensic detector."""

    kind: ArtifactKind
    mime_type: str
    data: bytes
    file_name: str


class DetectorResult(BaseModel):
    """Combined findings and visual evidence produced by a detector pass."""

    findings: list[FraudFinding] = Field(default_factory=list)
    evidence: list[tuple[int, GeneratedEvidence]] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Persisted Fraud Shield analysis returned by REST routes."""

    id: str
    case_id: str | None
    account_id: str | None
    mode: AnalysisMode
    risk_score: int = Field(ge=0, le=100)
    severity: FraudSeverity
    short_circuit_recommended: bool
    requires_four_eyes: bool
    findings: list[FraudFinding] = Field(default_factory=list)
    generated_artifacts: list[ArtifactRef] = Field(default_factory=list)
    explanation: str | None = None
    created_at: datetime


class FingerprintMatch(BaseModel):
    """Recycled-template perceptual-hash match against an earlier case."""

    fingerprint_id: str
    prior_analysis_id: str
    prior_case_id: str | None
    page: int = Field(ge=1)
    hamming_distance: int = Field(ge=0)


class PageFingerprint(BaseModel):
    """Perceptual hashes formatted as 64-character bitstrings."""

    page: int = Field(ge=1)
    phash_bits: str
    dhash_bits: str
