"""Playground visitors: who owns a workflow in demo mode (None outside it, and for examples).

Revision ID: 1_1
Revises: 1_0
Create Date: 2026-11-13 15:51:18.846768
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1_1"
down_revision: str | None = "1_0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("visitor_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_workflows_visitor_id"), "workflows", ["visitor_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflows_visitor_id"), table_name="workflows")
    op.drop_column("workflows", "visitor_id")
