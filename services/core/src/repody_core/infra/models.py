"""Database tables for ``repody_core`` (domain-agnostic cases, approvals, audit log)."""

from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repody_common.contracts import ArtifactKind, ModuleSource
from repody_core.infra.db import Base, CreatedAt, UpdatedAt, UtcDateTime
from repody_core.schemas.approvals import ApprovalStatus
from repody_core.schemas.cases import CaseStatus, PipelineStatus


class Case(Base):
    """Domain-agnostic unit of work (documents, pure JSON payloads, or external refs)."""

    __tablename__ = "cases"
    __table_args__ = (Index("ix_cases_account_status", "account_id", "status"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str | None] = mapped_column(index=True)
    external_ref: Mapped[str | None] = mapped_column(index=True)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[CaseStatus] = mapped_column(default="open")
    created_by: Mapped[str] = mapped_column(default="")
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class Artifact(Base):
    """S3-backed immutable artifact attached to a case by any module."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    module: Mapped[ModuleSource] = mapped_column(default="core")
    kind: Mapped[ArtifactKind] = mapped_column(default="source_document")
    storage_key: Mapped[str]
    sha256: Mapped[str]
    mime_type: Mapped[str]
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[CreatedAt]

    case: Mapped[Case] = relationship(back_populates="artifacts")


class PipelineRun(Base):
    """Multi-module durable pipeline execution tracked by Hatchet."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    status: Mapped[PipelineStatus] = mapped_column(default="queued")
    hatchet_run_id: Mapped[str | None]
    created_at: Mapped[CreatedAt]
    finished_at: Mapped[UtcDateTime | None]


class ApprovalTask(Base):
    """Four-Eyes (Maker-Checker) approval checkpoint with DB-level actor separation."""

    __tablename__ = "approval_tasks"
    __table_args__ = (
        CheckConstraint(
            "checker_sub IS NULL OR maker_sub IS NULL OR checker_sub <> maker_sub",
            name="ck_approval_tasks_four_eyes_distinct_actors",
        ),
        Index("ix_approval_tasks_case_status", "case_id", "status"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    stage_name: Mapped[str]
    status: Mapped[ApprovalStatus] = mapped_column(default="waiting_maker")
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    payload_sha256: Mapped[str]
    maker_sub: Mapped[str | None]
    maker_note: Mapped[str] = mapped_column(Text, default="")
    maker_decided_at: Mapped[UtcDateTime | None]
    checker_sub: Mapped[str | None]
    checker_note: Mapped[str] = mapped_column(Text, default="")
    checker_decided_at: Mapped[UtcDateTime | None]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class FieldOverride(Base):
    """Immutable per-field edit record written during Maker review."""

    __tablename__ = "field_overrides"

    id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    approval_task_id: Mapped[str] = mapped_column(
        ForeignKey("approval_tasks.id", ondelete="CASCADE"), index=True
    )
    field_path: Mapped[str]
    before_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    after_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    actor_sub: Mapped[str]
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[CreatedAt]


class AuditEvent(Base):
    """Append-only SHA-256 hash-chained regulatory audit ledger."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_created", "created_at"),)

    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=False), unique=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    actor_sub: Mapped[str]
    account_id: Mapped[str | None] = mapped_column(index=True)
    module: Mapped[str]
    action: Mapped[str]
    resource_id: Mapped[str] = mapped_column(index=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    prev_hash: Mapped[str]
    event_hash: Mapped[str]
    created_at: Mapped[CreatedAt]


class UsageEntry(Base):
    """Module-agnostic metering ledger (IDP pages, Fraud checks, Browser runs)."""

    __tablename__ = "usage_entries"

    id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(index=True)
    module: Mapped[ModuleSource]
    unit_kind: Mapped[str]
    quantity: Mapped[int] = mapped_column(BigInteger)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"))
    pending: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[CreatedAt]
    settled_at: Mapped[UtcDateTime | None]
