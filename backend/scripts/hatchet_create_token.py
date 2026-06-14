#!/usr/bin/env python3
"""Create a Hatchet API token for audit-workbench workers (run once after hatchet-lite starts)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time


def _create_via_admin(config_dir: str, name: str) -> str:
    result = subprocess.run(
        [
            "/hatchet/hatchet-admin",
            "--config",
            config_dir,
            "token",
            "create",
            "--name",
            name,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "hatchet-admin failed")
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("hatchet-admin returned empty token")
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Hatchet client token for workers/API")
    parser.add_argument("--url", default=os.getenv("HATCHET_SERVER_URL", "http://localhost:8888"))
    parser.add_argument("--config", default=os.getenv("HATCHET_CONFIG_DIR", "/config"))
    parser.add_argument("--name", default="audit-workbench")
    parser.add_argument("--out", default="", help="Write token to file (optional)")
    args = parser.parse_args()

    if args.out and os.path.isfile(args.out):
        with open(args.out, encoding="utf-8") as fh:
            existing = fh.read().strip()
        if existing:
            print(json.dumps({"token": existing, "host": args.url, "reused": True}))
            return 0

    last_exc: Exception | None = None
    for attempt in range(30):
        try:
            token = _create_via_admin(args.config, args.name)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as fh:
                    fh.write(token)
            print(json.dumps({"token": token, "host": args.url}))
            return 0
        except Exception as exc:
            last_exc = exc
            time.sleep(2)
    print(f"Failed to create Hatchet token: {last_exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
