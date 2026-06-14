"""Drop legacy run_outbox table (Hatchet replaces transactional outbox)."""

import sqlalchemy as sa
from alembic import op

revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_run_outbox_status_created_at", table_name="run_outbox")
    op.drop_table("run_outbox")


def downgrade() -> None:
    op.create_table(
        "run_outbox",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("queue", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_run_outbox_status_created_at",
        "run_outbox",
        ["status", "created_at"],
    )
