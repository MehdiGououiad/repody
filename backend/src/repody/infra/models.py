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

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repody.infra.db import Base, CreatedAt, UpdatedAt, UtcDateTime
from repody.schemas.credits import CreditKind
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
    # The account that owns it (repody.app.scope): a client company (its Keycloak group,
    # ``client-<name>``) or a playground visitor. None: a shared workflow, which every account
    # reads and duplicates but cannot change or run (the examples).
    account_id: Mapped[str | None] = mapped_column(index=True)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_status_created", "status", "created_at"),
        Index("ix_runs_workflow_created", "workflow_id", "created_at"),
        # The dashboard's windows (by creation) and the operations page's hourly counts (by finish).
        Index("ix_runs_created", "created_at"),
        Index("ix_runs_finished", "finished_at"),
        # A retried request with the same Idempotency-Key returns the run it started.
        Index(
            "uq_runs_client_idempotency",
            "client_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
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
    task_run_id: Mapped[str | None]  # its Hatchet run, to cancel it
    account_id: Mapped[str | None] = mapped_column(index=True)  # its workflow's, when started
    client_key: Mapped[str | None]  # who started it: the API key's hash prefix or the user
    idempotency_key: Mapped[str | None]
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


class CreditEntry(Base):
    """The credit ledger (repody.app.credits): an account's balance is the sum of its entries.

    A grant adds credits. A run's entry holds its estimate (negative, ``pending``) from the moment
    it is queued, then is settled once: the pages it sent the model (done), its estimate (failed
    after it started), or nothing (failed before it started). Entries outlive the run they charge
    (retention deletes runs, never entries), so usage and balances stay whole.
    """

    __tablename__ = "credit_entries"

    id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(index=True)
    kind: Mapped[CreditKind]
    amount: Mapped[int] = mapped_column(BigInteger)  # credits: 1 = one page sent to the model
    pending: Mapped[bool] = mapped_column(default=False)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), unique=True
    )
    pages: Mapped[int] = mapped_column(default=0)  # pages sent to the model (runs)
    model_ms: Mapped[int] = mapped_column(BigInteger, default=0)  # extraction time (runs)
    note: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(default="")  # who granted, or the run's client
    created_at: Mapped[CreatedAt]
    settled_at: Mapped[UtcDateTime | None]
