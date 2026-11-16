"""Cloudflare Turnstile: the site's form proves a person sent it; the server checks the token.
https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
"""

import httpx
import structlog

from repody.settings import get_settings

log = structlog.get_logger(__name__)

SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TIMEOUT_SECONDS = 10


def enabled() -> bool:
    # Compose passes an unset variable as "": that is no secret, not an empty one.
    secret = get_settings().turnstile_secret
    return secret is not None and bool(secret.get_secret_value())


async def verify(token: str, ip: str | None) -> bool:
    """Whether Cloudflare accepts the token (single use, five minutes). Off without a secret."""
    secret = get_settings().turnstile_secret
    if secret is None or not enabled():
        return True
    if not token:
        return False
    data = {"secret": secret.get_secret_value(), "response": token}
    if ip:
        data["remoteip"] = ip
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            body = (await client.post(SITEVERIFY, data=data)).json()
    except (httpx.HTTPError, ValueError) as exc:
        log.error("turnstile_unreachable", error=repr(exc))
        return False
    if not body.get("success"):
        log.warning("turnstile_refused", errors=body.get("error-codes"))
    return bool(body.get("success"))
