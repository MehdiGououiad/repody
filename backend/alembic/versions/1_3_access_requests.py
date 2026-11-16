"""1.3: access requests from the site (``access_requests``, repody.app.access), and the audit
log's two new actions (request.approved, request.declined).

Revision ID: 1_3
Revises: 1_2
Create Date: 2026-11-16 19:41:12.125702
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

ACTIONS = (
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
)
NEW_ACTIONS = ("request.approved", "request.declined")

revision: str = "1_3"
down_revision: str | None = "1_2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("sector", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_hash", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "approved",
                "declined",
                name="ck_access_requests_status",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_requests")),
    )
    op.create_index(op.f("ix_access_requests_email"), "access_requests", ["email"], unique=False)
    op.create_index(
        "ix_access_requests_ip_created", "access_requests", ["ip_hash", "created_at"], unique=False
    )
    op.create_index(
        "ix_access_requests_status_created",
        "access_requests",
        ["status", "created_at"],
        unique=False,
    )

    _action_check(ACTIONS + NEW_ACTIONS)


def _action_check(actions: tuple[str, ...]) -> None:
    """admin_events.action is a VARCHAR with a CHECK of its values (the models' Literal)."""
    op.drop_constraint("ck_admin_events_action", "admin_events", type_="check")
    values = ", ".join(f"'{a}'" for a in actions)
    op.create_check_constraint("ck_admin_events_action", "admin_events", f"action IN ({values})")


def downgrade() -> None:
    op.execute(f"DELETE FROM admin_events WHERE action IN {NEW_ACTIONS!r}")
    _action_check(ACTIONS)
    op.drop_index("ix_access_requests_status_created", table_name="access_requests")
    op.drop_index("ix_access_requests_ip_created", table_name="access_requests")
    op.drop_index(op.f("ix_access_requests_email"), table_name="access_requests")
    op.drop_table("access_requests")
