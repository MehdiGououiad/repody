"""Drop unused extraction_quality_mode from documents.

Revision ID: c1d2e3f4a5b6
Revises: b8c9d0e1f2a3
Create Date: 2026-07-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("documents", "extraction_quality_mode")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("extraction_quality_mode", sa.String(length=16), nullable=True),
    )
