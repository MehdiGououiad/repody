"""Initial repody_fraud schema with pgvector support."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import BIT
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "fraud_analyses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=True),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column(
            "mode",
            sa.Enum("standalone", "pre_check", "post_verify", name="analysismode", native_enum=False),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("clean", "low", "medium", "high", "critical", name="fraudseverity", native_enum=False),
            nullable=False,
        ),
        sa.Column("short_circuit_recommended", sa.Boolean(), nullable=False),
        sa.Column("requires_four_eyes", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("generated_artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_fraud_risk_score_bounds"),
        sa.PrimaryKeyConstraint("id", name="pk_fraud_analyses"),
    )
    op.create_index("ix_fraud_analyses_case_id", "fraud_analyses", ["case_id"])
    op.create_index("ix_fraud_analyses_account_id", "fraud_analyses", ["account_id"])
    op.create_index("ix_fraud_analyses_account_case", "fraud_analyses", ["account_id", "case_id"])

    op.create_table(
        "fraud_findings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("detector", sa.String(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("clean", "low", "medium", "high", "critical", name="fraudseverity", native_enum=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_artifact_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["fraud_analyses.id"],
            name="fk_fraud_findings_analysis_id_fraud_analyses",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fraud_findings"),
    )
    op.create_index("ix_fraud_findings_analysis_id", "fraud_findings", ["analysis_id"])

    op.create_table(
        "document_fingerprints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=True),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("phash_bits", BIT(64), nullable=False),
        sa.Column("dhash_bits", BIT(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["fraud_analyses.id"],
            name="fk_document_fingerprints_analysis_id_fraud_analyses",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_fingerprints"),
    )
    op.create_index("ix_document_fingerprints_analysis_id", "document_fingerprints", ["analysis_id"])
    op.create_index("ix_document_fingerprints_case_id", "document_fingerprints", ["case_id"])
    op.create_index("ix_document_fingerprints_account_id", "document_fingerprints", ["account_id"])
    op.create_index("ix_fingerprints_account_sha", "document_fingerprints", ["account_id", "sha256"])


def downgrade() -> None:
    op.drop_table("document_fingerprints")
    op.drop_table("fraud_findings")
    op.drop_table("fraud_analyses")
