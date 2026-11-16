"""1.2: the admin area's audit log (``admin_events``, repody.app.admin).

Revision ID: 1_2
Revises: 1_1
Create Date: 2026-11-16 15:49:14.702172
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1_2"
down_revision: str | None = "1_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "client.created",
                "client.disabled",
                "client.enabled",
                "user.invited",
                "user.role_changed",
                "user.disabled",
                "user.enabled",
                "user.password_reset",
                "user.removed",
                "credits.granted",
                "workflow.assigned",
                name="ck_admin_events_action",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_events")),
    )
    op.create_index(
        op.f("ix_admin_events_account_id"), "admin_events", ["account_id"], unique=False
    )
    op.create_index("ix_admin_events_created", "admin_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_events_created", table_name="admin_events")
    op.drop_index(op.f("ix_admin_events_account_id"), table_name="admin_events")
    op.drop_table("admin_events")
