"""1.1: accounts, the credit ledger, idempotent runs.

- ``workflows.visitor_id`` becomes ``account_id`` (a client company or a playground visitor;
  repody.app.scope), kept as it is; runs get their workflow's.
- ``credit_entries``: the credit ledger (repody.app.credits).
- ``runs.client_key`` and ``runs.idempotency_key``: a retried start returns the same run.

Revision ID: 1_1
Revises: 1_0
Create Date: 2026-11-16 11:07:26.857787
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1_1"
down_revision: str | None = "1_0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "grant",
                "run",
                name="ck_credit_entries_kind",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("pending", sa.Boolean(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=False),
        sa.Column("model_ms", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_credit_entries_run_id_runs"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_entries")),
        sa.UniqueConstraint("run_id", name=op.f("uq_credit_entries_run_id")),
    )
    op.create_index(
        op.f("ix_credit_entries_account_id"), "credit_entries", ["account_id"], unique=False
    )
    op.add_column("runs", sa.Column("account_id", sa.String(), nullable=True))
    op.add_column("runs", sa.Column("client_key", sa.String(), nullable=True))
    op.add_column("runs", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.create_index(op.f("ix_runs_account_id"), "runs", ["account_id"], unique=False)
    op.create_index(
        "uq_runs_client_idempotency",
        "runs",
        ["client_key", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.alter_column("workflows", "visitor_id", new_column_name="account_id")
    op.execute("ALTER INDEX ix_workflows_visitor_id RENAME TO ix_workflows_account_id")
    op.execute(
        "UPDATE runs SET account_id = workflows.account_id FROM workflows"
        " WHERE runs.workflow_id = workflows.id"
    )


def downgrade() -> None:
    op.execute("ALTER INDEX ix_workflows_account_id RENAME TO ix_workflows_visitor_id")
    op.alter_column("workflows", "account_id", new_column_name="visitor_id")
    op.drop_index(
        "uq_runs_client_idempotency",
        table_name="runs",
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_index(op.f("ix_runs_account_id"), table_name="runs")
    op.drop_column("runs", "idempotency_key")
    op.drop_column("runs", "client_key")
    op.drop_column("runs", "account_id")
    op.drop_index(op.f("ix_credit_entries_account_id"), table_name="credit_entries")
    op.drop_table("credit_entries")
