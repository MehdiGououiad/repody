#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema for frontend codegen."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "lib" / "api" / "openapi.json"


def main() -> int:
    from audit_workbench.main import create_app

    schema = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    raise SystemExit(main())
