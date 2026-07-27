"""Add runs.last_activity_at for stage-aware stale reap.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE runs SET last_activity_at = COALESCE(started_at, created_at) "
            "WHERE last_activity_at IS NULL"
        )
    )
    op.create_index("ix_runs_status_last_activity", "runs", ["status", "last_activity_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_status_last_activity", table_name="runs")
    op.drop_column("runs", "last_activity_at")
