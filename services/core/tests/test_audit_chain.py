"""Tests for RFC 8785 canonical hashing and SHA-256 audit chain verification."""

from repody_core.schemas.hashing import (
    GENESIS_HASH,
    AuditChainItem,
    canonical_sha256,
    compute_event_hash,
    verify_audit_chain,
)


def _make_item(
    prev_hash: str,
    *,
    event_id: str,
    action: str,
    detail: dict[str, object],
) -> AuditChainItem:
    created_at_iso = "2026-11-27T16:00:00+00:00"
    event_hash = compute_event_hash(
        prev_hash,
        event_id=event_id,
        actor_sub="maker-1",
        account_id="client-bank-a",
        module="core",
        action=action,
        resource_id="case-1",
        detail=dict(detail),
        created_at_iso=created_at_iso,
    )
    return AuditChainItem(
        id=event_id,
        actor_sub="maker-1",
        account_id="client-bank-a",
        module="core",
        action=action,
        resource_id="case-1",
        detail=dict(detail),
        created_at_iso=created_at_iso,
        prev_hash=prev_hash,
        event_hash=event_hash,
    )


def test_rfc8785_canonical_sha256_is_key_order_independent() -> None:
    a = {"b": 2, "a": {"z": True, "m": [1, 2, 3]}}
    b = {"a": {"m": [1, 2, 3], "z": True}, "b": 2}
    assert canonical_sha256(a) == canonical_sha256(b)


def test_audit_chain_detects_tampering_and_missing_links() -> None:
    e1 = _make_item(GENESIS_HASH, event_id="evt-1", action="case.created", detail={"x": 1})
    e2 = _make_item(e1.event_hash, event_id="evt-2", action="approval.created", detail={"x": 2})
    e3 = _make_item(e2.event_hash, event_id="evt-3", action="approval.approved", detail={"x": 3})

    assert verify_audit_chain([e1, e2, e3]) == (True, 3, None)

    tampered_e2 = AuditChainItem(
        id=e2.id,
        actor_sub=e2.actor_sub,
        account_id=e2.account_id,
        module=e2.module,
        action=e2.action,
        resource_id=e2.resource_id,
        detail={"x": 999},
        created_at_iso=e2.created_at_iso,
        prev_hash=e2.prev_hash,
        event_hash=e2.event_hash,
    )
    assert verify_audit_chain([e1, tampered_e2, e3]) == (False, 1, "evt-2")

    # Deleting link 2 breaks link 3's prev_hash pointer.
    assert verify_audit_chain([e1, e3]) == (False, 1, "evt-3")
