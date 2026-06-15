"""Re-add run dispatch outbox for durable Hatchet enqueue after DB commit."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "l2m3n4o5p6q7"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("worker_pool", sa.String(length=16), nullable=True))
    op.create_table(
        "run_dispatch_outbox",
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("pool", sa.String(16), nullable=False, server_default="fast"),
        sa.Column("workflow_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_run_dispatch_outbox_status_created",
        "run_dispatch_outbox",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_run_dispatch_outbox_status_created", table_name="run_dispatch_outbox")
    op.drop_table("run_dispatch_outbox")
    op.drop_column("runs", "worker_pool")
