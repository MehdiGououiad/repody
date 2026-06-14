"""document extraction mode and ocr model

Revision ID: b2c3d4e5f6a7
Revises: a1c2d3e4f5b6
Create Date: 2026-05-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1c2d3e4f5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("extraction_mode", sa.String(32), nullable=False, server_default="auto"),
    )
    op.add_column(
        "documents",
        sa.Column("ocr_model", sa.String(128), nullable=True),
    )
    op.add_column(
        "workflows",
        sa.Column("default_llm_model", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflows", "default_llm_model")
    op.drop_column("documents", "ocr_model")
    op.drop_column("documents", "extraction_mode")
