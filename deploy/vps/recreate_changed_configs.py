# ruff: noqa: T201, S603 - a deploy script: it runs fixed docker compose commands, and reports on stdout
"""Recreate the services whose inline configs changed (deploy.yml, right after `up`).

Compose recreates a container when its service definition changes, and the content of a
`configs:` entry is not part of that definition: a release that changes only Alloy's or Loki's
config would leave the old one running. This keeps each config's SHA-256 (never its content,
which can hold secrets) in .config-hashes.json beside the stack, and recreates the services that
read a config whose hash changed. Postgres is left out: its only config runs on an empty volume.

Run from the stack's directory: python3 tools/recreate_changed_configs.py
"""

import hashlib
import json
import subprocess
from pathlib import Path

COMPOSE = ["docker", "compose", "--env-file", ".env", "--env-file", "release.env"]
STATE = Path(".config-hashes.json")
NEVER = {"postgres"}  # postgres-init only runs on an empty data volume


def main() -> None:
    rendered = subprocess.run(
        [*COMPOSE, "config", "--format", "json"], check=True, capture_output=True, text=True
    ).stdout
    stack = json.loads(rendered)
    hashes = {
        name: hashlib.sha256(config.get("content", "").encode()).hexdigest()
        for name, config in stack.get("configs", {}).items()
    }
    previous = json.loads(STATE.read_text()) if STATE.exists() else {}
    changed = {name for name, digest in hashes.items() if previous.get(name) != digest}
    services = sorted(
        name
        for name, service in stack.get("services", {}).items()
        if name not in NEVER
        and any(config.get("source") in changed for config in service.get("configs", []))
    )
    if services:
        print(f"configs changed ({', '.join(sorted(changed))}): recreating {' '.join(services)}")
        subprocess.run(
            [
                *COMPOSE,
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                "300",
                "--force-recreate",
                "--no-deps",
                *services,
            ],
            check=True,
        )
    else:
        print("no config changed")
    STATE.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    STATE.chmod(0o600)


if __name__ == "__main__":
    main()
