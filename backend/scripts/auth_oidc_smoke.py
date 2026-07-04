#!/usr/bin/env python3
"""Smoke-test Keycloak password grant + API JWT authorization.

Usage (stack with --with=auth):
  python scripts/auth_oidc_smoke.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
for _path in (_BACKEND / "src", _BACKEND):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from audit_workbench.auth.keycloak_token import fetch_password_grant_token_sync  # noqa: E402


def _get(url: str, token: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, res.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _post_json(url: str, token: str, payload: dict) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, res.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _fetch_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str:
    return fetch_password_grant_token_sync(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        timeout=30.0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="OIDC + Casbin smoke test")
    parser.add_argument("--keycloak", default="http://127.0.0.1:8080")
    parser.add_argument("--realm", default="repody")
    parser.add_argument("--client-id", default="repody-web")
    parser.add_argument("--client-secret", default="repody-web-dev-secret")
    parser.add_argument("--username", default="operator@repody.local")
    parser.add_argument("--password", default="repody-dev")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    token_url = f"{args.keycloak}/realms/{args.realm}/protocol/openid-connect/token"
    try:
        access = _fetch_token(
            token_url=token_url,
            client_id=args.client_id,
            client_secret=args.client_secret,
            username=args.username,
            password=args.password,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    status, body = _get(f"{args.base_url}/v1/workflows", access)
    print(f"GET /v1/workflows -> {status}")
    if status != 200:
        print(body, file=sys.stderr)
        return 1

    try:
        viewer_access = _fetch_token(
            token_url=token_url,
            client_id=args.client_id,
            client_secret=args.client_secret,
            username="viewer@repody.local",
            password=args.password,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    blocked_status, _ = _post_json(
        f"{args.base_url}/v1/workflows",
        viewer_access,
        {"name": "forbidden", "description": "", "owner": "viewer"},
    )
    print(f"POST /v1/workflows as viewer -> {blocked_status}")
    if blocked_status != 403:
        print("Expected viewer to be forbidden on workflow create", file=sys.stderr)
        return 1

    print("OIDC smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
