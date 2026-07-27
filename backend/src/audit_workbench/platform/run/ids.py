"""Pure helpers for run create — no session / framework I/O."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime


def new_id(prefix: str, *, uuid_hex: Callable[[], str] | None = None) -> str:
    """Prefixed opaque id (`{prefix}-{12 hex}` by default)."""
    hex_part = (uuid_hex or (lambda: uuid.uuid4().hex[:12]))()
    return f"{prefix}-{hex_part}"


def new_run_id(
    source: str,
    *,
    now: Callable[[], datetime] | None = None,
    uuid_hex: Callable[[], str] | None = None,
) -> str:
    clock = now or (lambda: datetime.now(UTC))
    hex8 = uuid_hex or (lambda: uuid.uuid4().hex[:8])
    prefix = "AUD-TEST" if source == "test" else "AUD"
    return f"{prefix}-{int(clock().timestamp() * 1000)}-{hex8()}"


def document_row_id(*, uuid_hex: Callable[[], str] | None = None) -> str:
    return new_id("rdoc", uuid_hex=uuid_hex)
