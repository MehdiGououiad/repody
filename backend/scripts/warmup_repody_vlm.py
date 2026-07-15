#!/usr/bin/env python3
"""Prime local NuExtract3 / llama-server with a production-shaped warmup request."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from audit_workbench.extraction.repody_vlm import warmup_repody_vlm  # noqa: E402

# Written by this script so detached `pnpm llamacpp:serve` can exit while warmup continues.
_WARMUP_MARKER = (
    Path(__file__).resolve().parents[2] / "deploy" / "llamacpp" / "logs" / ".warmup-complete"
)


async def main() -> int:
    status = await warmup_repody_vlm()
    print(f"repody_vlm_warmup: {status}")
    ok = status in {"ok", "skipped", "disabled"}
    if ok:
        _WARMUP_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _WARMUP_MARKER.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
