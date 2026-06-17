from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from audit_workbench.db.base import Base


class WorkflowStatus(str, enum.Enum):
    active = "active"
    draft = "draft"
    paused = "paused"
    archived = "archived"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class OverallStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default=WorkflowStatus.draft.value)
    owner: Mapped[str] = mapped_column(String(128), default="Me")
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_key_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    rules: Mapped[list[WorkflowRule]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    runs: Mapped[list[Run]] = relationship(back_populates="workflow")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    document_type: Mapped[str] = mapped_column(String(128), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    extraction_mode: Mapped[str] = mapped_column(String(32), default="document_model")
    validation_mode: Mapped[str] = mapped_column(String(32), default="logic_only")
    ocr_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    workflow: Mapped[Workflow] = relationship(back_populates="documents")
    schema_fields: Mapped[list[SchemaField]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class SchemaField(Base):
    __tablename__ = "schema_fields"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[Document] = relationship(back_populates="schema_fields")


class WorkflowRule(Base):
    __tablename__ = "workflow_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="")
    kind: Mapped[str] = mapped_column(String(16), default="logic")
    scope: Mapped[str] = mapped_column(String(16), default="intra")
    body: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="reject")
    applies_to: Mapped[list[Any]] = mapped_column(JSON, default=list)
    conditions: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    condition_junction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    workflow: Mapped[Workflow] = relationship(back_populates="rules")


class RuleTemplate(Base):
    __tablename__ = "rule_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16))
    scope: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="flag")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_workflow_created", "workflow_id", "created_at"),
        Index("ix_runs_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(16), default="test")
    status: Mapped[str] = mapped_column(String(16), default=RunStatus.queued.value)
    overall_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_total: Mapped[int] = mapped_column(Integer, default=0)
    summary_passed: Mapped[int] = mapped_column(Integer, default=0)
    summary_failed: Mapped[int] = mapped_column(Integer, default=0)
    fields_extracted: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    run_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    run_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    worker_pool: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[Workflow] = relationship(back_populates="runs")
    documents: Mapped[list[RunDocument]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    rule_results: Mapped[list[RuleResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RunDocument(Base):
    __tablename__ = "run_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_type: Mapped[str] = mapped_column(String(128), default="")
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extraction_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped[Run] = relationship(back_populates="documents")
    fields: Mapped[list[ExtractedField]] = relationship(
        back_populates="run_document", cascade="all, delete-orphan"
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_document_id: Mapped[str] = mapped_column(
        ForeignKey("run_documents.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    value: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(32), default="string")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extracted: Mapped[bool] = mapped_column(default=True)
    flagged: Mapped[bool] = mapped_column(default=False)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    run_document: Mapped[RunDocument] = relationship(back_populates="fields")


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16))
    scope: Mapped[str] = mapped_column(String(16), default="intra")
    status: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    expression: Mapped[str] = mapped_column(Text, default="")
    affected_fields: Mapped[list[Any]] = mapped_column(JSON, default=list)
    detail: Mapped[str] = mapped_column(Text, default="")
    expected_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actual_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    run: Mapped[Run] = relationship(back_populates="rule_results")


class RunDispatchOutbox(Base):
    __tablename__ = "run_dispatch_outbox"
    __table_args__ = (Index("ix_run_dispatch_outbox_status_created", "status", "created_at"),)

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pool: Mapped[str] = mapped_column(String(16), default="fast")
    workflow_id: Mapped[str] = mapped_column(String(64), default="")
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    dispatch_attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UploadIntent(Base):
    __tablename__ = "upload_intents"
    __table_args__ = (
        Index("ux_upload_intents_storage_key", "storage_key", unique=True),
        Index("ix_upload_intents_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
