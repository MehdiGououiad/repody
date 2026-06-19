"""Add per-document NuExtract extraction instructions.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("extraction_instructions", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("documents", "extraction_instructions", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "extraction_instructions")
