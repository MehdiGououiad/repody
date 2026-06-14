"""Add run_metadata and run document extraction fields for audit reports."""

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("run_metadata", sa.JSON(), nullable=True))
    op.add_column("run_documents", sa.Column("file_name", sa.String(512), nullable=True))
    op.add_column("run_documents", sa.Column("extraction_meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("run_documents", "extraction_meta")
    op.drop_column("run_documents", "file_name")
    op.drop_column("runs", "run_metadata")
