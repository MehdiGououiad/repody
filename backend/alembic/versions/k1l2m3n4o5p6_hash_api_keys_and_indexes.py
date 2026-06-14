"""Hash API keys, add hints, and performance indexes."""

from __future__ import annotations

import hashlib

import sqlalchemy as sa
from alembic import op

revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _hint(raw: str) -> str:
    prefix = raw[:12] if len(raw) >= 12 else raw
    return f"{prefix}••••••••"


def upgrade() -> None:
    op.add_column("workflows", sa.Column("api_key_hint", sa.String(length=32), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, api_key FROM workflows WHERE api_key IS NOT NULL")
    ).fetchall()
    for row in rows:
        raw = row.api_key
        if not raw or len(raw) == 64:
            try:
                int(raw, 16)
                continue
            except (TypeError, ValueError):
                pass
        digest = _hash_key(raw)
        hint = _hint(raw)
        conn.execute(
            sa.text(
                "UPDATE workflows SET api_key = :digest, api_key_hint = :hint WHERE id = :id"
            ),
            {"digest": digest, "hint": hint, "id": row.id},
        )

    op.create_index("ix_runs_workflow_created", "runs", ["workflow_id", "created_at"])
    op.create_index("ix_runs_status", "runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_index("ix_runs_workflow_created", table_name="runs")
    op.drop_column("workflows", "api_key_hint")
