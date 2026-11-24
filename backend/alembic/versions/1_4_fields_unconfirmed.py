"""1.4: a run's fields that a second read did not confirm (``runs.fields_unconfirmed``,
repody.extraction.pipeline), counted like ``fields_extracted`` so lists need no document JSON.

Revision ID: 1_4
Revises: 1_3
Create Date: 2026-11-24 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1_4"
down_revision: str | None = "1_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("fields_unconfirmed", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("runs", "fields_unconfirmed")
