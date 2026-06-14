"""add run progress

Revision ID: a1c2d3e4f5b6
Revises: 9b24af3aa3c5
Create Date: 2026-05-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c2d3e4f5b6"
down_revision: Union[str, None] = "9b24af3aa3c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE runs ADD COLUMN IF NOT EXISTS progress JSON")


def downgrade() -> None:
    op.drop_column("runs", "progress")
