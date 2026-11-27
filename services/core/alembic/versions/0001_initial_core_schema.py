"""Initial ``repody_core`` schema (cases, artifacts, pipelines, Four-Eyes, audit chain).

Revision ID: 0001_initial_core_schema
Revises:
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_core_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ``repody_core`` tables and regulatory constraints."""
    op.create_table(
        "cases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("external_ref", sa.String(), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "waiting_maker",
                "waiting_checker",
                "approved",
                "rejected",
                "failed",
                name="casestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
    )
    op.create_index(op.f("ix_cases_account_id"), "cases", ["account_id"], unique=False)
    op.create_index("ix_cases_account_status", "cases", ["account_id", "status"], unique=False)
    op.create_index(op.f("ix_cases_external_ref"), "cases", ["external_ref"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column(
            "module",
            sa.Enum("core", "idp", "fraud", "operator", name="modulesource", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "source_document",
                "pdf_revision_diff",
                "forensic_heatmap",
                "browser_screenshot",
                "playwright_trace",
                "json_report",
                name="artifactkind",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_artifacts_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifacts")),
    )
    op.create_index(op.f("ix_artifacts_case_id"), "artifacts", ["case_id"], unique=False)

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("stages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "waiting_approval",
                "done",
                "rejected",
                "failed",
                name="pipelinestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("hatchet_run_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_pipeline_runs_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_runs")),
    )
    op.create_index(op.f("ix_pipeline_runs_case_id"), "pipeline_runs", ["case_id"], unique=False)

    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("stage_name", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "waiting_maker",
                "waiting_checker",
                "approved",
                "rejected",
                "returned_to_maker",
                name="approvalstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("payload_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_sha256", sa.String(), nullable=False),
        sa.Column("maker_sub", sa.String(), nullable=True),
        sa.Column("maker_note", sa.Text(), nullable=False),
        sa.Column("maker_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checker_sub", sa.String(), nullable=True),
        sa.Column("checker_note", sa.Text(), nullable=False),
        sa.Column("checker_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "checker_sub IS NULL OR maker_sub IS NULL OR checker_sub <> maker_sub",
            name="ck_approval_tasks_four_eyes_distinct_actors",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_approval_tasks_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_tasks")),
    )
    op.create_index(
        op.f("ix_approval_tasks_case_id"), "approval_tasks", ["case_id"], unique=False
    )
    op.create_index(
        "ix_approval_tasks_case_status", "approval_tasks", ["case_id", "status"], unique=False
    )

    op.create_table(
        "field_overrides",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("approval_task_id", sa.String(), nullable=False),
        sa.Column("field_path", sa.String(), nullable=False),
        sa.Column("before_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("actor_sub", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approval_task_id"],
            ["approval_tasks.id"],
            name=op.f("fk_field_overrides_approval_task_id_approval_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_field_overrides_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_overrides")),
    )
    op.create_index(
        op.f("ix_field_overrides_approval_task_id"),
        "field_overrides",
        ["approval_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_field_overrides_case_id"), "field_overrides", ["case_id"], unique=False
    )

    op.create_table(
        "audit_events",
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("actor_sub", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prev_hash", sa.String(), nullable=False),
        sa.Column("event_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        sa.UniqueConstraint("seq", name=op.f("uq_audit_events_seq")),
    )
    op.create_index(
        op.f("ix_audit_events_account_id"), "audit_events", ["account_id"], unique=False
    )
    op.create_index(
        "ix_audit_events_created", "audit_events", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_resource_id"), "audit_events", ["resource_id"], unique=False
    )

    op.create_table(
        "usage_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column(
            "module",
            sa.Enum("core", "idp", "fraud", "operator", name="modulesource", native_enum=False),
            nullable=False,
        ),
        sa.Column("unit_kind", sa.String(), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=True),
        sa.Column("pending", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_usage_entries_case_id_cases"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_entries")),
    )
    op.create_index(
        op.f("ix_usage_entries_account_id"), "usage_entries", ["account_id"], unique=False
    )


def downgrade() -> None:
    """Drop ``repody_core`` tables."""
    op.drop_table("usage_entries")
    op.drop_table("audit_events")
    op.drop_table("field_overrides")
    op.drop_table("approval_tasks")
    op.drop_table("pipeline_runs")
    op.drop_table("artifacts")
    op.drop_table("cases")
