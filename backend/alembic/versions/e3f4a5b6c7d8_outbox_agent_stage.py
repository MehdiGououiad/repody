"""Add agent_stage to run_dispatch_outbox for staged agent handoff.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "run_dispatch_outbox",
        sa.Column("agent_stage", sa.String(length=32), nullable=False, server_default="idp"),
    )


def downgrade() -> None:
    op.drop_column("run_dispatch_outbox", "agent_stage")
