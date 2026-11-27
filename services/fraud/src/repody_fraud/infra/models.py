"""Database tables for ``repody_fraud`` (analyses, findings, and perceptual fingerprints)."""

from typing import Any

from pgvector.sqlalchemy import BIT
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repody_common.contracts import FraudSeverity
from repody_fraud.infra.db import Base, CreatedAt
from repody_fraud.schemas.analyses import AnalysisMode


class FraudAnalysis(Base):
    """Forensic analysis summary row."""

    __tablename__ = "fraud_analyses"
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_fraud_risk_score_bounds"),
        Index("ix_fraud_analyses_account_case", "account_id", "case_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str | None] = mapped_column(index=True)
    account_id: Mapped[str | None] = mapped_column(index=True)
    mode: Mapped[AnalysisMode]
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    severity: Mapped[FraudSeverity] = mapped_column(default="clean")
    short_circuit_recommended: Mapped[bool] = mapped_column(default=False)
    requires_four_eyes: Mapped[bool] = mapped_column(default=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    generated_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[CreatedAt]

    findings: Mapped[list["FraudFindingRow"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class FraudFindingRow(Base):
    """Explainable finding attached to a ``FraudAnalysis``."""

    __tablename__ = "fraud_findings"

    id: Mapped[str] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("fraud_analyses.id", ondelete="CASCADE"), index=True
    )
    detector: Mapped[str]
    tier: Mapped[int] = mapped_column(Integer)
    code: Mapped[str]
    severity: Mapped[FraudSeverity]
    title: Mapped[str]
    detail: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB)
    evidence_artifact_id: Mapped[str | None]

    analysis: Mapped[FraudAnalysis] = relationship(back_populates="findings")


class DocumentFingerprint(Base):
    """Perceptual pHash / dHash stored as pgvector ``BIT(64)`` for template-reuse search."""

    __tablename__ = "document_fingerprints"
    __table_args__ = (Index("ix_fingerprints_account_sha", "account_id", "sha256"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("fraud_analyses.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[str | None] = mapped_column(index=True)
    account_id: Mapped[str | None] = mapped_column(index=True)
    page: Mapped[int] = mapped_column(Integer, default=1)
    sha256: Mapped[str]
    phash_bits: Mapped[str] = mapped_column(BIT(64))
    dhash_bits: Mapped[str] = mapped_column(BIT(64))
    created_at: Mapped[CreatedAt]
