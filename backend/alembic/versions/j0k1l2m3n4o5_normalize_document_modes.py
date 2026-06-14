"""Normalize legacy extraction_mode + validation_mode migration."""

import sqlalchemy as sa
from alembic import op

revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def _normalize_pair(extraction_mode: str | None, validation_mode: str | None) -> tuple[str, str]:
    from audit_workbench.extraction.processing_paths import (
        normalize_read_path_id,
        parse_validation_mode,
    )

    read_id = normalize_read_path_id(extraction_mode)
    val_id = parse_validation_mode(validation_mode, extraction_mode=extraction_mode)
    return read_id, val_id


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, extraction_mode, validation_mode FROM documents")
    ).fetchall()
    for doc_id, extraction_mode, validation_mode in rows:
        read_id, val_id = _normalize_pair(extraction_mode, validation_mode)
        conn.execute(
            sa.text(
                "UPDATE documents SET extraction_mode = :read_id, validation_mode = :val_id WHERE id = :doc_id"
            ),
            {"read_id": read_id, "val_id": val_id, "doc_id": doc_id},
        )


def downgrade() -> None:
    pass
