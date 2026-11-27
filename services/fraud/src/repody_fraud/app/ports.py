"""Protocol ports for persistence and immutable artifact storage."""

from typing import Protocol

from repody_common.contracts import ArtifactRef, FraudFinding, FraudSeverity
from repody_fraud.schemas.analyses import (
    AnalysisMode,
    AnalysisResponse,
    FingerprintMatch,
    PageFingerprint,
)


class FraudStore(Protocol):
    """Persistence port for Fraud Shield analyses and pgvector perceptual fingerprints."""

    async def ping(self) -> bool: ...

    async def save_analysis(
        self,
        *,
        analysis_id: str,
        case_id: str | None,
        account_id: str | None,
        mode: AnalysisMode,
        risk_score: int,
        severity: FraudSeverity,
        short_circuit_recommended: bool,
        requires_four_eyes: bool,
        findings: list[FraudFinding],
        generated_artifacts: list[ArtifactRef],
        explanation: str | None,
    ) -> AnalysisResponse: ...

    async def get_analysis(
        self,
        analysis_id: str,
        *,
        account: str | None,
    ) -> AnalysisResponse | None: ...

    async def store_fingerprints(
        self,
        *,
        analysis_id: str,
        case_id: str | None,
        account_id: str | None,
        sha256: str,
        fingerprints: list[PageFingerprint],
    ) -> None: ...

    async def find_similar_fingerprints(
        self,
        *,
        phash_bits: str,
        account: str | None,
        max_distance: int,
        exclude_case_id: str | None,
    ) -> list[FingerprintMatch]: ...


class ArtifactStorage(Protocol):
    """S3-compatible object storage port for reading source files and storing evidence PNGs."""

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get_bytes(self, key: str) -> bytes: ...
