"""RFC 8785 (JCS) canonical hashing and SHA-256 audit hash-chain verification."""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import jcs
from pydantic_core import to_jsonable_python

GENESIS_HASH = "0" * 64


def canonical_sha256(payload: Any) -> str:
    """Compute a deterministic SHA-256 hex digest using RFC 8785 (JCS)."""
    jsonable = to_jsonable_python(payload)
    raw = jcs.canonicalize(jsonable)
    canonical_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_event_hash(
    prev_hash: str,
    *,
    event_id: str,
    actor_sub: str,
    account_id: str | None,
    module: str,
    action: str,
    resource_id: str,
    detail: dict[str, Any],
    created_at_iso: str,
) -> str:
    """Compute the chained SHA-256 digest linking an audit event to ``prev_hash``."""
    envelope = {
        "prev_hash": prev_hash,
        "id": event_id,
        "actor_sub": actor_sub,
        "account_id": account_id,
        "module": module,
        "action": action,
        "resource_id": resource_id,
        "detail": detail,
        "created_at": created_at_iso,
    }
    return canonical_sha256(envelope)


@dataclass(frozen=True, slots=True)
class AuditChainItem:
    """Minimal projection needed to verify an audit event chain."""

    id: str
    actor_sub: str
    account_id: str | None
    module: str
    action: str
    resource_id: str
    detail: dict[str, Any]
    created_at_iso: str
    prev_hash: str
    event_hash: str


def verify_audit_chain(events: Sequence[AuditChainItem]) -> tuple[bool, int, str | None]:
    """Verify hash-chain integrity across ordered audit events.

    Returns ``(valid, checked_count, first_broken_id)``.
    """
    expected_prev = GENESIS_HASH
    checked = 0
    for item in events:
        if item.prev_hash != expected_prev:
            return False, checked, item.id
        expected_hash = compute_event_hash(
            item.prev_hash,
            event_id=item.id,
            actor_sub=item.actor_sub,
            account_id=item.account_id,
            module=item.module,
            action=item.action,
            resource_id=item.resource_id,
            detail=item.detail,
            created_at_iso=item.created_at_iso,
        )
        if item.event_hash != expected_hash:
            return False, checked, item.id
        expected_prev = item.event_hash
        checked += 1
    return True, checked, None
