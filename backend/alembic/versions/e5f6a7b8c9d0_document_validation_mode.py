"""Add validation_mode to documents."""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("validation_mode", sa.String(32), nullable=False, server_default="logic_only"),
    )
    op.alter_column("documents", "extraction_mode", server_default="paddle")


def downgrade() -> None:
    op.alter_column("documents", "extraction_mode", server_default="auto")
    op.drop_column("documents", "validation_mode")
