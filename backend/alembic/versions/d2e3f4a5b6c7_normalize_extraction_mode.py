"""Normalize legacy document extraction_mode values to document_model.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_MODES = (
    "auto",
    "vlm",
    "vision",
    "pdf_text",
    "text_logic",
    "ocr",
)


def upgrade() -> None:
    bind = op.get_bind()
    legacy = ", ".join(f"'{mode}'" for mode in _LEGACY_MODES)
    bind.execute(
        sa.text(
            f"""
            UPDATE documents
            SET extraction_mode = 'document_model'
            WHERE extraction_mode IS NULL
               OR btrim(extraction_mode) = ''
               OR lower(extraction_mode) IN ({legacy})
               OR lower(extraction_mode) <> 'document_model'
            """
        )
    )


def downgrade() -> None:
    # Irreversible data normalization — no-op.
    pass
