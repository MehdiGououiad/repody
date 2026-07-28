"""runs queue and worker_pool indexes for hot path scale

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_runs_status_created_id "
        "ON runs (status, created_at, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_runs_status_worker_pool "
        "ON runs (status, worker_pool)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_runs_status_worker_pool")
    op.execute("DROP INDEX IF EXISTS ix_runs_status_created_id")
