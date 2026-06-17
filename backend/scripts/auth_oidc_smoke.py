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
import urllib.parse
import urllib.request


def _post_form(url: str, data: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


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
    tokens = _post_form(
        token_url,
        {
            "grant_type": "password",
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "username": args.username,
            "password": args.password,
        },
    )
    access = tokens.get("access_token")
    if not access:
        print("Token response missing access_token", file=sys.stderr)
        return 1

    status, body = _get(f"{args.base_url}/v1/workflows", access)
    print(f"GET /v1/workflows -> {status}")
    if status != 200:
        print(body, file=sys.stderr)
        return 1

    viewer_tokens = _post_form(
        token_url,
        {
            "grant_type": "password",
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "username": "viewer@repody.local",
            "password": args.password,
        },
    )
    viewer_access = viewer_tokens["access_token"]
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
