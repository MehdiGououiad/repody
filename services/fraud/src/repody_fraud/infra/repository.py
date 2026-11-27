"""PostgreSQL + pgvector repository implementing ``FraudStore``."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody_common.contracts import ArtifactRef, FraudFinding, FraudSeverity
from repody_common.ids import new_id
from repody_fraud.infra.models import DocumentFingerprint, FraudAnalysis, FraudFindingRow
from repody_fraud.schemas.analyses import (
    AnalysisMode,
    AnalysisResponse,
    FingerprintMatch,
    PageFingerprint,
)


def _analysis_to_schema(row: FraudAnalysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=row.id,
        case_id=row.case_id,
        account_id=row.account_id,
        mode=row.mode,
        risk_score=row.risk_score,
        severity=row.severity,
        short_circuit_recommended=row.short_circuit_recommended,
        requires_four_eyes=row.requires_four_eyes,
        findings=[
            FraudFinding(
                detector=f.detector,
                tier=f.tier,  # type: ignore[arg-type]
                code=f.code,
                severity=f.severity,
                title=f.title,
                detail=f.detail,
                page=f.page,
                bbox=tuple(f.bbox) if f.bbox else None,  # type: ignore[arg-type]
                evidence_artifact_id=f.evidence_artifact_id,
            )
            for f in row.findings
        ],
        generated_artifacts=[ArtifactRef.model_validate(item) for item in row.generated_artifacts],
        explanation=row.explanation,
        created_at=row.created_at,
    )


class SqlFraudStore:
    """Async SQLAlchemy 2.1 + pgvector persistence backend for Fraud Shield."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> bool:
        await self._session.execute(text("SELECT 1"))
        return True

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
    ) -> AnalysisResponse:
        now = datetime.now(UTC)
        row = FraudAnalysis(
            id=analysis_id,
            case_id=case_id,
            account_id=account_id,
            mode=mode,
            risk_score=risk_score,
            severity=severity,
            short_circuit_recommended=short_circuit_recommended,
            requires_four_eyes=requires_four_eyes,
            explanation=explanation,
            generated_artifacts=[a.model_dump(mode="json") for a in generated_artifacts],
            created_at=now,
            findings=[
                FraudFindingRow(
                    id=new_id("ff"),
                    analysis_id=analysis_id,
                    detector=item.detector,
                    tier=item.tier,
                    code=item.code,
                    severity=item.severity,
                    title=item.title,
                    detail=item.detail,
                    page=item.page,
                    bbox=list(item.bbox) if item.bbox else None,
                    evidence_artifact_id=item.evidence_artifact_id,
                )
                for item in findings
            ],
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row, attribute_names=["findings"])
        return _analysis_to_schema(row)

    async def get_analysis(
        self,
        analysis_id: str,
        *,
        account: str | None,
    ) -> AnalysisResponse | None:
        stmt = (
            select(FraudAnalysis)
            .options(selectinload(FraudAnalysis.findings))
            .where(FraudAnalysis.id == analysis_id)
        )
        if account is not None:
            stmt = stmt.where(FraudAnalysis.account_id == account)
        row = await self._session.scalar(stmt)
        return _analysis_to_schema(row) if row else None

    async def store_fingerprints(
        self,
        *,
        analysis_id: str,
        case_id: str | None,
        account_id: str | None,
        sha256: str,
        fingerprints: list[PageFingerprint],
    ) -> None:
        now = datetime.now(UTC)
        for fp in fingerprints:
            self._session.add(
                DocumentFingerprint(
                    id=new_id("fp"),
                    analysis_id=analysis_id,
                    case_id=case_id,
                    account_id=account_id,
                    page=fp.page,
                    sha256=sha256,
                    phash_bits=fp.phash_bits,
                    dhash_bits=fp.dhash_bits,
                    created_at=now,
                )
            )
        await self._session.commit()

    async def find_similar_fingerprints(
        self,
        *,
        phash_bits: str,
        account: str | None,
        max_distance: int,
        exclude_case_id: str | None,
    ) -> list[FingerprintMatch]:
        distance_expr: Any = func.hamming_distance(DocumentFingerprint.phash_bits, phash_bits)
        stmt = (
            select(
                DocumentFingerprint.id,
                DocumentFingerprint.analysis_id,
                DocumentFingerprint.case_id,
                DocumentFingerprint.page,
                distance_expr.label("distance"),
            )
            .where(distance_expr <= max_distance)
            .order_by(distance_expr.asc())
            .limit(5)
        )
        if account is not None:
            stmt = stmt.where(DocumentFingerprint.account_id == account)
        if exclude_case_id is not None:
            stmt = stmt.where(DocumentFingerprint.case_id != exclude_case_id)
        rows = (await self._session.execute(stmt)).all()
        return [
            FingerprintMatch(
                fingerprint_id=row.id,
                prior_analysis_id=row.analysis_id,
                prior_case_id=row.case_id,
                page=row.page,
                hamming_distance=int(row.distance),
            )
            for row in rows
        ]
