"""Initial platform schema (squashed 2026-07).

Revision ID: f0a1b2c3d4e5
Revises:
Create Date: 2026-07-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rule_templates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_key", sa.String(length=128), nullable=True),
        sa.Column("api_key_hint", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("extraction_mode", sa.String(length=32), nullable=False),
        sa.Column("validation_mode", sa.String(length=32), nullable=False),
        sa.Column("document_model_id", sa.String(length=128), nullable=True),
        sa.Column("extraction_instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "markdown_extraction",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_workflow_id"), "documents", ["workflow_id"], unique=False)
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("overall_status", sa.String(length=16), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("summary_total", sa.Integer(), nullable=False),
        sa.Column("summary_passed", sa.Integer(), nullable=False),
        sa.Column("summary_failed", sa.Integer(), nullable=False),
        sa.Column("fields_extracted", sa.Integer(), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=True),
        sa.Column("run_snapshot", sa.JSON(), nullable=True),
        sa.Column("run_metadata", sa.JSON(), nullable=True),
        sa.Column("worker_pool", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runs_workflow_id"), "runs", ["workflow_id"], unique=False)
    op.create_index("ix_runs_workflow_created", "runs", ["workflow_id", "created_at"], unique=False)
    op.create_index("ix_runs_status", "runs", ["status"], unique=False)
    op.create_index("ix_runs_status_worker_pool", "runs", ["status", "worker_pool"], unique=False)
    op.create_index("ix_runs_status_started_at", "runs", ["status", "started_at"], unique=False)
    op.create_index("ix_runs_status_created_at", "runs", ["status", "created_at"], unique=False)
    op.create_table(
        "workflow_rules",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("applies_to", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("condition_junction", sa.String(length=8), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_rules_workflow_id"), "workflow_rules", ["workflow_id"], unique=False
    )
    op.create_table(
        "run_dispatch_outbox",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("pool", sa.String(length=16), server_default="fast", nullable=False),
        sa.Column("workflow_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("dispatch_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_run_dispatch_outbox_status_created",
        "run_dispatch_outbox",
        ["status", "created_at"],
        unique=False,
    )
    op.create_table(
        "upload_intents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("owner_subject", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_upload_intents_storage_key",
        "upload_intents",
        ["storage_key"],
        unique=True,
    )
    op.create_index(
        "ix_upload_intents_created",
        "upload_intents",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "rule_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("affected_fields", sa.JSON(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("expected_value", sa.String(length=255), nullable=True),
        sa.Column("actual_value", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rule_results_run_id"), "rule_results", ["run_id"], unique=False)
    op.create_table(
        "run_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("document_type", sa.String(length=128), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("extraction_meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_run_documents_run_id"), "run_documents", ["run_id"], unique=False)
    op.create_table(
        "schema_fields",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("template_type", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_schema_fields_document_id"), "schema_fields", ["document_id"], unique=False
    )
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_document_id", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("extracted", sa.Boolean(), nullable=False),
        sa.Column("flagged", sa.Boolean(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["run_document_id"], ["run_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
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
    op.drop_index(op.f("ix_schema_fields_document_id"), table_name="schema_fields")
    op.drop_table("schema_fields")
    op.drop_index(op.f("ix_run_documents_run_id"), table_name="run_documents")
    op.drop_table("run_documents")
    op.drop_index(op.f("ix_rule_results_run_id"), table_name="rule_results")
    op.drop_table("rule_results")
    op.drop_index("ix_upload_intents_created", table_name="upload_intents")
    op.drop_index("ux_upload_intents_storage_key", table_name="upload_intents")
    op.drop_table("upload_intents")
    op.drop_index("ix_run_dispatch_outbox_status_created", table_name="run_dispatch_outbox")
    op.drop_table("run_dispatch_outbox")
    op.drop_index(op.f("ix_workflow_rules_workflow_id"), table_name="workflow_rules")
    op.drop_table("workflow_rules")
    op.drop_index("ix_runs_status_created_at", table_name="runs")
    op.drop_index("ix_runs_status_started_at", table_name="runs")
    op.drop_index("ix_runs_status_worker_pool", table_name="runs")
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_index("ix_runs_workflow_created", table_name="runs")
    op.drop_index(op.f("ix_runs_workflow_id"), table_name="runs")
    op.drop_table("runs")
    op.drop_index(op.f("ix_documents_workflow_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_table("workflows")
    op.drop_table("rule_templates")
