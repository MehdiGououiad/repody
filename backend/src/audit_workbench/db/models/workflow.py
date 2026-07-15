from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from audit_workbench.db.base import Base
from audit_workbench.db.models.enums import WorkflowStatus

if TYPE_CHECKING:
    from audit_workbench.db.models.run import Run


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
    document_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extraction_instructions: Mapped[str] = mapped_column(Text, default="")
    markdown_extraction: Mapped[bool] = mapped_column(default=False)
    extraction_icl_examples: Mapped[list[Any]] = mapped_column(JSON, default=list)

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
    template_type: Mapped[str] = mapped_column(String(64), default="verbatim-string")
    field_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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
