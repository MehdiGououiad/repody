"""Replace run_dispatch_outbox with runs.dispatched_at.

The API now sends the Taskiq task right after commit and stamps runs.dispatched_at;
maintenance re-sends queued runs whose dispatched_at is still NULL.

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h2i3j4k5l6m7"
down_revision: str | None = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    # Carry over sends the outbox recorded; anything past `queued` was dispatched by definition.
    op.execute(
        """
        UPDATE runs SET dispatched_at = o.dispatched_at
        FROM run_dispatch_outbox o
        WHERE o.run_id = runs.id AND o.dispatched_at IS NOT NULL
        """
    )
    op.execute(
        "UPDATE runs SET dispatched_at = created_at "
        "WHERE dispatched_at IS NULL AND status <> 'queued'"
    )
    op.drop_index("ix_run_dispatch_outbox_status_created", table_name="run_dispatch_outbox")
    op.drop_table("run_dispatch_outbox")


def downgrade() -> None:
    op.create_table(
        "run_dispatch_outbox",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("pool", sa.String(length=16), server_default="fast", nullable=False),
        sa.Column("workflow_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("dispatch_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agent_stage", sa.String(length=32), nullable=False, server_default="idp"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_run_dispatch_outbox_status_created",
        "run_dispatch_outbox",
        ["status", "created_at"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO run_dispatch_outbox (run_id, pool, workflow_id, status, dispatched_at)
        SELECT id, COALESCE(worker_pool, 'fast'), workflow_id,
               CASE WHEN dispatched_at IS NULL THEN 'pending' ELSE 'dispatched' END,
               dispatched_at
        FROM runs WHERE status = 'queued'
        """
    )
    op.drop_column("runs", "dispatched_at")
