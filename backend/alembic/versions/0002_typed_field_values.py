"""Extracted values keep their JSON type; NULL replaces the "—" placeholder.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Old rows hold text; keep it as a JSON string (numbers were text before, too).
    op.execute(
        "ALTER TABLE extracted_fields ALTER COLUMN value DROP NOT NULL, "
        "ALTER COLUMN value TYPE JSON USING CASE WHEN value = '—' THEN NULL ELSE to_json(value) END"
    )
    op.drop_column("extracted_fields", "extracted")


def downgrade() -> None:
    op.add_column(
        "extracted_fields",
        sa.Column("extracted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE extracted_fields SET extracted = value IS NOT NULL")
    op.execute(
        "ALTER TABLE extracted_fields ALTER COLUMN value TYPE TEXT "
        "USING COALESCE(value #>> '{}', '—'), ALTER COLUMN value SET NOT NULL"
    )
