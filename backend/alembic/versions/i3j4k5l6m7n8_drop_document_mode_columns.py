"""Drop per-document mode columns and leftover LLM rules.

There is one read path, one model and one validator (logic rules). Workflows still holding
an LLM rule could not be saved (rule validation rejects it), so those rules and the LLM
rule template are deleted. Historical rule_results are kept.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i3j4k5l6m7n8"
down_revision: str | None = "h2i3j4k5l6m7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ("extraction_mode", "validation_mode", "document_model_id", "native_pdf_auto")


def upgrade() -> None:
    op.execute("DELETE FROM workflow_rules WHERE kind = 'llm'")
    op.execute("DELETE FROM rule_templates WHERE kind = 'llm'")
    with op.batch_alter_table("documents") as batch:
        for name in _COLUMNS:
            batch.drop_column(name)


def downgrade() -> None:
    # Deleted LLM rules are not restored.
    with op.batch_alter_table("documents") as batch:
        batch.add_column(
            sa.Column(
                "extraction_mode",
                sa.String(length=32),
                nullable=False,
                server_default="document_model",
            )
        )
        batch.add_column(
            sa.Column(
                "validation_mode", sa.String(length=32), nullable=False, server_default="logic_only"
            )
        )
        batch.add_column(sa.Column("document_model_id", sa.String(length=128), nullable=True))
        batch.add_column(
            sa.Column(
                "native_pdf_auto", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
