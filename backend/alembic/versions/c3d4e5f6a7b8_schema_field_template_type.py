"""Add NuExtract template type to schema fields.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "schema_fields",
        sa.Column(
            "template_type",
            sa.String(length=32),
            nullable=False,
            server_default="verbatim-string",
        ),
    )
    op.alter_column("schema_fields", "template_type", server_default=None)


def downgrade() -> None:
    op.drop_column("schema_fields", "template_type")
