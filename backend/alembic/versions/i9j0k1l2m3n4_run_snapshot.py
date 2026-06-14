"""Add run_snapshot JSON for ephemeral workflow config per run."""

import sqlalchemy as sa
from alembic import op

revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("run_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "run_snapshot")
