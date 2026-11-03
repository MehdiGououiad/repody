"""Validate Keycloak-issued JWT access tokens (OIDC / JWKS) with PyJWT."""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any

import jwt
from fastapi.security.utils import get_authorization_scheme_param
from jwt import PyJWKClient, PyJWKSet

from repody.infra.auth.principal import APP_REALM_ROLES, Principal
from repody.settings import Settings, get_settings

_JWKS_CACHE_TTL = 300


class JwtValidationError(Exception):
    pass


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=_JWKS_CACHE_TTL)


def _issuer(settings: Settings) -> str:
    if not settings.oidc_issuer:
        raise JwtValidationError("OIDC issuer is not configured")
    return settings.oidc_issuer.rstrip("/")


def _jwks_url(settings: Settings) -> str:
    return settings.oidc_jwks_url or f"{_issuer(settings)}/protocol/openid-connect/certs"


def _signing_key(token: str, settings: Settings) -> Any:
    if settings.oidc_jwks_json:
        # Inline JWKS (tests / air-gapped): pick the key by the token's `kid`.
        keys = PyJWKSet.from_dict(json.loads(settings.oidc_jwks_json))
        kid = str(jwt.get_unverified_header(token).get("kid") or "")
        try:
            return keys[kid].key
        except KeyError as exc:
            raise JwtValidationError("No matching JWK for token") from exc
    return _jwks_client(_jwks_url(settings)).get_signing_key_from_jwt(token).key


def _roles_from_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    realm_roles = (payload.get("realm_access") or {}).get("roles") or []
    groups = [str(group).lstrip("/") for group in payload.get("groups") or []]
    return tuple(sorted({str(role) for role in [*realm_roles, *groups]} & APP_REALM_ROLES))


def extract_bearer(authorization: str | None) -> str | None:
    """Return the token from an ``Authorization: Bearer <token>`` header, else None."""
    scheme, token = get_authorization_scheme_param((authorization or "").strip())
    return token.strip() or None if scheme.lower() == "bearer" else None


def principal_from_bearer(token: str | None, settings: Settings | None = None) -> Principal:
    settings = settings or get_settings()
    if not token:
        raise JwtValidationError("Missing bearer token")
    issuers = [_issuer(settings), *(a.rstrip("/") for a in settings.accepted_oidc_issuer_aliases())]
    try:
        payload = jwt.decode(
            token,
            _signing_key(token, settings),
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=issuers,
            options={"verify_aud": bool(settings.oidc_audience), "require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise JwtValidationError(str(exc)) from exc
    email = payload.get("email")
    return Principal(
        subject=str(payload["sub"]),
        roles=_roles_from_payload(payload),
        email=str(email) if email else None,
    )


async def warm_jwks_cache(settings: Settings | None = None) -> None:
    """Fetch the JWKS once at startup so the first request does not pay for it."""
    settings = settings or get_settings()
    if not settings.oidc_enabled or settings.oidc_jwks_json:
        return
    await asyncio.to_thread(_jwks_client(_jwks_url(settings)).get_jwk_set)
