"""Regulatory audit trail and health schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    """One entry in the SHA-256 hash-chained audit ledger."""

    seq: int
    id: str
    actor_sub: str
    account_id: str | None
    module: str
    action: str
    resource_id: str
    detail: dict[str, Any]
    prev_hash: str
    event_hash: str
    created_at: datetime


class AuditChainVerificationResponse(BaseModel):
    """Result of verifying the hash chain over stored audit events."""

    valid: bool
    checked_count: int
    first_broken_id: str | None = None


class CoreHealthResponse(BaseModel):
    """Service liveness/readiness report."""

    status: Literal["ok", "degraded"]
    database: bool | None = None
    oidc_enabled: bool = False
