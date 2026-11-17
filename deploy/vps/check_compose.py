# ruff: noqa: T201 - a script: it reports on stdout
"""Refuse a stack that reaches outside itself, before it is started (deploy.yml).

Reads ``docker compose config --format json`` on stdin. Two stacks share the server
(production and staging), and a staging deploy runs whatever master holds without a person
looking at it at deploy time: its compose.yaml must not mount host paths (the other stack's
.env, the Docker socket), use another project's volumes or networks, or ask for privileges or
the host's namespaces. Exits 1 with the reasons.
"""

import json
import sys

ESCALATIONS = ("privileged", "cap_add", "devices", "userns_mode")
HOST_NAMESPACES = ("pid", "ipc", "network_mode", "uts")


def problems(config: dict) -> list[str]:
    found = []
    for name, service in config.get("services", {}).items():
        for volume in service.get("volumes", []):
            if volume.get("type") == "bind":
                found.append(f"{name}: mounts the host path {volume.get('source')}")
        found += [f"{name}: sets {key}" for key in ESCALATIONS if service.get(key)]
        for key in HOST_NAMESPACES:
            value = str(service.get(key) or "")
            if value == "host" or value.startswith(("container:", "service:")):
                found.append(f"{name}: {key} {value}")
    for kind in ("volumes", "networks"):
        for name, spec in (config.get(kind) or {}).items():
            if (spec or {}).get("external"):
                found.append(f"{kind[:-1]} {name} is external")
    return found


if __name__ == "__main__":
    reasons = problems(json.load(sys.stdin))
    if reasons:
        sys.exit("compose.yaml reaches outside its stack:\n  " + "\n  ".join(reasons))
    print("compose.yaml stays inside its stack")
