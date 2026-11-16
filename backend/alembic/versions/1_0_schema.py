"""1.0 schema: the whole database for Repody 1.0 (no earlier revision upgrades to it).

Generated from the models (``alembic revision --autogenerate``). Every Literal column has a
CHECK of its values named ``ck_<table>_<column>``, as the models' naming convention names it.

Revision ID: 1_0
Revises:
Create Date: 2026-11-10 15:25:12.476267
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1_0"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "active",
                "archived",
                name="ck_workflows_status",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_key_hash", sa.String(), nullable=True),
        sa.Column("api_key_hint", sa.String(), nullable=True),
        sa.Column("visitor_id", sa.String(), nullable=True),
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
            "status = 'archived' OR (status = 'active') = (deployed_at IS NOT NULL)",
            name="ck_workflows_deployed_when_active",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflows")),
    )
    op.create_index(op.f("ix_workflows_visitor_id"), "workflows", ["visitor_id"], unique=False)
    op.create_table(
        "runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "test",
                "api",
                name="ck_runs_source",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "done",
                "failed",
                name="ck_runs_status",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.Enum(
                "passed",
                "warning",
                "failed",
                name="ck_runs_outcome",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rules_total", sa.Integer(), nullable=False),
        sa.Column("rules_passed", sa.Integer(), nullable=False),
        sa.Column("rules_failed", sa.Integer(), nullable=False),
        sa.Column("fields_extracted", sa.Integer(), nullable=False),
        sa.Column("extraction_ms", sa.Integer(), nullable=False),
        sa.Column("validation_ms", sa.Integer(), nullable=False),
        sa.Column("task_run_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(outcome IS NOT NULL) = (status = 'done')", name="ck_runs_outcome_when_done"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name=op.f("fk_runs_workflow_id_workflows"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )
    op.create_index("ix_runs_status_created", "runs", ["status", "created_at"], unique=False)
    op.create_index("ix_runs_workflow_created", "runs", ["workflow_id", "created_at"], unique=False)
    op.create_index("ix_runs_created", "runs", ["created_at"], unique=False)
    op.create_index("ix_runs_finished", "runs", ["finished_at"], unique=False)
    op.create_table(
        "rule_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "scope",
            sa.Enum(
                "intra",
                "cross",
                name="ck_rule_results_scope",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "reject",
                "flag",
                name="ck_rule_results_severity",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "passed",
                "failed",
                "skipped",
                name="ck_rule_results_status",
                native_enum=False,
                create_constraint=True,
                length=None,
            ),
            nullable=False,
        ),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("affected_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_rule_results_run_id_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_results")),
    )
    op.create_index(op.f("ix_rule_results_run_id"), "rule_results", ["run_id"], unique=False)
    op.create_table(
        "run_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_run_documents_run_id_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_documents")),
    )
    op.create_index(op.f("ix_run_documents_run_id"), "run_documents", ["run_id"], unique=False)
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_document_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "value", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True
        ),
        sa.Column("flagged", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_document_id"],
            ["run_documents.id"],
            name=op.f("fk_extracted_fields_run_document_id_run_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extracted_fields")),
    )
    op.create_index(
        op.f("ix_extracted_fields_run_document_id"),
        "extracted_fields",
        ["run_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_extracted_fields_run_document_id"), table_name="extracted_fields")
    op.drop_table("extracted_fields")
    op.drop_index(op.f("ix_run_documents_run_id"), table_name="run_documents")
    op.drop_table("run_documents")
    op.drop_index(op.f("ix_rule_results_run_id"), table_name="rule_results")
    op.drop_table("rule_results")
    op.drop_index("ix_runs_finished", table_name="runs")
    op.drop_index("ix_runs_created", table_name="runs")
    op.drop_index("ix_runs_workflow_created", table_name="runs")
    op.drop_index("ix_runs_status_created", table_name="runs")
    op.drop_table("runs")
    op.drop_index(op.f("ix_workflows_visitor_id"), table_name="workflows")
    op.drop_table("workflows")
