#!/usr/bin/env python3
"""Prime local NuExtract3 / llama-server with a production-shaped warmup request."""

from __future__ import annotations

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from audit_workbench.extraction.repody_vlm import warmup_repody_vlm  # noqa: E402


async def main() -> int:
    status = await warmup_repody_vlm()
    print(f"repody_vlm_warmup: {status}")
    return 0 if status in {"ok", "skipped", "disabled"} else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
