"""Database tables.

A workflow's documents and rules are one JSON ``definition`` (validated by
``schemas.workflow.WorkflowDefinition``); each run keeps its own copy, so editing a
workflow never changes a run that is queued or done.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repody.infra.db import Base
from repody.schemas.run import Outcome, RuleStatus, RunStatus

# Lifecycles (repody.app.lifecycle): the CHECK constraints keep every row in a state the
# transitions produce. Kept in step with the migration (alembic/versions).
WorkflowState = Literal["draft", "active", "archived"]


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'archived') "
            "AND (status = 'archived' OR (status = 'active') = (deployed_at IS NOT NULL))",
            name="ck_workflows_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[WorkflowState] = mapped_column(String(16), default="draft")
    owner: Mapped[str] = mapped_column(String(128), default="")
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    api_key_hash: Mapped[str | None] = mapped_column(String(64))
    api_key_hint: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_status_created", "status", "created_at"),
        Index("ix_runs_workflow_created", "workflow_id", "created_at"),
        CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name="ck_runs_status"),
        CheckConstraint(
            "(outcome IS NOT NULL) = (status = 'done') "
            "AND (outcome IS NULL OR outcome IN ('passed', 'warning', 'failed'))",
            name="ck_runs_outcome",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    source: Mapped[Literal["test", "api"]] = mapped_column(String(8))
    status: Mapped[RunStatus] = mapped_column(String(16), default="queued")
    outcome: Mapped[Outcome | None] = mapped_column(String(16))  # set when done
    error: Mapped[str | None] = mapped_column(Text)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    rules_total: Mapped[int] = mapped_column(Integer, default=0)
    rules_passed: Mapped[int] = mapped_column(Integer, default=0)
    rules_failed: Mapped[int] = mapped_column(Integer, default=0)
    fields_extracted: Mapped[int] = mapped_column(Integer, default=0)
    extraction_ms: Mapped[int] = mapped_column(Integer, default=0)
    validation_ms: Mapped[int] = mapped_column(Integer, default=0)
    # NULL while queued means the task was never sent; maintenance sends it again.
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow: Mapped[Workflow] = relationship()
    documents: Mapped[list[RunDocument]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunDocument.position"
    )
    rule_results: Mapped[list[RuleResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RuleResult.position"
    )


class RunDocument(Base):
    """One uploaded file of a run and what the model extracted from it."""

    __tablename__ = "run_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    document_id: Mapped[str] = mapped_column(String(64))
    document_type: Mapped[str] = mapped_column(String(128), default="")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(128))
    storage_key: Mapped[str] = mapped_column(String(255))
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # ExtractionMeta

    run: Mapped[Run] = relationship(back_populates="documents")
    fields: Mapped[list[ExtractedField]] = relationship(
        back_populates="run_document",
        cascade="all, delete-orphan",
        order_by="ExtractedField.position",
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_document_id: Mapped[str] = mapped_column(
        ForeignKey("run_documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    key: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(32))
    # The model's JSON value in the field's template type; NULL when not extracted.
    value: Mapped[Any] = mapped_column(JSON(none_as_null=True), nullable=True)
    flagged: Mapped[bool] = mapped_column(default=False)

    run_document: Mapped[RunDocument] = relationship(back_populates="fields")


class RuleResult(Base):
    __tablename__ = "rule_results"
    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed', 'skipped')", name="ck_rule_results_status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    rule_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    scope: Mapped[str] = mapped_column(String(8))
    severity: Mapped[str] = mapped_column(String(8))
    status: Mapped[RuleStatus] = mapped_column(String(8))
    expression: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    affected_fields: Mapped[list[str]] = mapped_column(JSON, default=list)

    run: Mapped[Run] = relationship(back_populates="rule_results")
