"""Add index on run_outbox(status, created_at) for maintenance sweeps."""

from alembic import op

revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_run_outbox_status_created_at",
        "run_outbox",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_run_outbox_status_created_at", table_name="run_outbox")
