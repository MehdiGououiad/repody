"""Add upload intents for presigned upload binding.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_intents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("owner_subject", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_upload_intents_storage_key",
        "upload_intents",
        ["storage_key"],
        unique=True,
    )
    op.create_index(
        "ix_upload_intents_created",
        "upload_intents",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_upload_intents_created", table_name="upload_intents")
    op.drop_index("ux_upload_intents_storage_key", table_name="upload_intents")
    op.drop_table("upload_intents")
