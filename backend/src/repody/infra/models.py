"""Database tables.

A workflow's documents and rules are one JSON ``definition`` (validated by
``schemas.workflow.WorkflowDefinition``); each run keeps its own copy, so editing a
workflow never changes a run that is queued or done.

Every ``Literal`` column is a VARCHAR with a CHECK constraint listing its values, generated
from the same ``Literal`` the API uses (``Base.type_annotation_map``). The two table CHECKs
below tie a lifecycle state to the columns it implies (repody.app.lifecycle).
"""

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repody.infra.db import Base, CreatedAt, UpdatedAt, UtcDateTime
from repody.schemas.rule import Scope, Severity
from repody.schemas.run import Outcome, RuleStatus, RunStatus, Source
from repody.schemas.workflow import WorkflowState


def new_id(prefix: str) -> str:
    """An id with a readable prefix, e.g. ``run-019a…``: a UUIDv7, so ids sort by creation time
    (good for B-tree indexes and for listing newest first)."""
    return f"{prefix}-{uuid.uuid7().hex}"


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        # Active means deployed; archived is final whatever it was before.
        CheckConstraint(
            "status = 'archived' OR (status = 'active') = (deployed_at IS NOT NULL)",
            name="ck_workflows_deployed_when_active",
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[WorkflowState] = mapped_column(default="draft")
    owner: Mapped[str] = mapped_column(default="")
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    deployed_at: Mapped[UtcDateTime | None]
    api_key_hash: Mapped[str | None]
    api_key_hint: Mapped[str | None]
    # Demo mode: the playground visitor who owns it; None for everyone else's workflows (and,
    # in the playground, the shared examples).
    visitor_id: Mapped[str | None] = mapped_column(index=True)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_status_created", "status", "created_at"),
        Index("ix_runs_workflow_created", "workflow_id", "created_at"),
        CheckConstraint(
            "(outcome IS NOT NULL) = (status = 'done')", name="ck_runs_outcome_when_done"
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    source: Mapped[Source]
    status: Mapped[RunStatus] = mapped_column(default="queued")
    outcome: Mapped[Outcome | None]  # set when done
    error: Mapped[str | None] = mapped_column(Text)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rules_total: Mapped[int] = mapped_column(default=0)
    rules_passed: Mapped[int] = mapped_column(default=0)
    rules_failed: Mapped[int] = mapped_column(default=0)
    fields_extracted: Mapped[int] = mapped_column(default=0)
    extraction_ms: Mapped[int] = mapped_column(default=0)
    validation_ms: Mapped[int] = mapped_column(default=0)
    # NULL while queued means the task was never sent; maintenance sends it again.
    dispatched_at: Mapped[UtcDateTime | None]
    created_at: Mapped[CreatedAt]
    started_at: Mapped[UtcDateTime | None]
    finished_at: Mapped[UtcDateTime | None]

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

    id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    document_id: Mapped[str]
    document_type: Mapped[str] = mapped_column(default="")
    file_name: Mapped[str] = mapped_column(default="")
    mime_type: Mapped[str]
    storage_key: Mapped[str]
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # ExtractionMeta

    run: Mapped[Run] = relationship(back_populates="documents")
    fields: Mapped[list[ExtractedField]] = relationship(
        back_populates="run_document",
        cascade="all, delete-orphan",
        order_by="ExtractedField.position",
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(primary_key=True)
    run_document_id: Mapped[str] = mapped_column(
        ForeignKey("run_documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(default=0)
    key: Mapped[str]
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str]
    # The model's JSON value in the field's template type; NULL when not extracted.
    value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    flagged: Mapped[bool] = mapped_column(default=False)

    run_document: Mapped[RunDocument] = relationship(back_populates="fields")


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    rule_id: Mapped[str]
    name: Mapped[str]
    scope: Mapped[Scope]
    severity: Mapped[Severity]
    status: Mapped[RuleStatus]
    expression: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    affected_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)

    run: Mapped[Run] = relationship(back_populates="rule_results")
