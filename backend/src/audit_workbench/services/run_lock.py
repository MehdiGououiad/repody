"""Stable Postgres advisory lock keys for run coordination."""

from __future__ import annotations

import hashlib


def advisory_lock_key(run_id: str) -> int:
    """Deterministic int64 key for pg_advisory_xact_lock (stable across processes)."""
    digest = hashlib.sha256(run_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF
