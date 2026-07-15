"""Validate Keycloak-issued JWT access tokens (OIDC / JWKS)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, cast

import httpx
import jwt
from jwt import PyJWKClient

from audit_workbench.auth.principal import APP_REALM_ROLES, Principal
from audit_workbench.settings import Settings, get_settings

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


def _accepted_issuers(settings: Settings) -> set[str]:
    issuers = {_issuer(settings)}
    issuers.update(
        alias.rstrip("/") for alias in settings.accepted_oidc_issuer_aliases()
    )
    return issuers


def _validate_issuer(payload: dict[str, Any], settings: Settings) -> None:
    token_issuer = str(payload.get("iss") or "").rstrip("/")
    if token_issuer not in _accepted_issuers(settings):
        raise JwtValidationError("Invalid issuer")


def _jwks_url(settings: Settings) -> str:
    if settings.oidc_jwks_url:
        return settings.oidc_jwks_url
    return f"{_issuer(settings)}/protocol/openid-connect/certs"


def _roles_from_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    realm_access = payload.get("realm_access") or {}
    realm_roles = realm_access.get("roles") or []
    groups = payload.get("groups") or []
    merged = {str(role) for role in realm_roles if str(role) in APP_REALM_ROLES}
    for group in groups:
        name = str(group).lstrip("/")
        if name in APP_REALM_ROLES:
            merged.add(name)
    return tuple(sorted(merged))


def _decode_options(settings: Settings) -> dict[str, bool]:
    return {"verify_aud": bool(settings.oidc_audience), "verify_iss": False}


def _finalize_payload(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    _validate_issuer(payload, settings)
    return payload


def _decode_with_jwks(token: str, settings: Settings) -> dict[str, Any]:
    if settings.oidc_jwks_json:
        jwks = json.loads(settings.oidc_jwks_json)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        keys = {key.get("kid"): key for key in jwks.get("keys", [])}
        jwk_data = keys.get(kid) or (jwks["keys"][0] if jwks.get("keys") else None)
        if not jwk_data:
            raise JwtValidationError("No matching JWK for token")
        from jwt.algorithms import RSAAlgorithm

        public_key = cast(Any, RSAAlgorithm.from_jwk(json.dumps(jwk_data)))
        return _finalize_payload(
            jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options=cast(Any, _decode_options(settings)),
                audience=settings.oidc_audience,
            ),
            settings,
        )

    client = _jwks_client(_jwks_url(settings))
    signing_key = client.get_signing_key_from_jwt(token)
    return _finalize_payload(
        jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options=cast(Any, _decode_options(settings)),
            audience=settings.oidc_audience,
        ),
        settings,
    )


def principal_from_bearer(token: str | None, settings: Settings | None = None) -> Principal:
    settings = settings or get_settings()
    if not token:
        raise JwtValidationError("Missing bearer token")
    try:
        payload = _decode_with_jwks(token, settings)
    except jwt.PyJWTError as exc:
        raise JwtValidationError(str(exc)) from exc

    subject = payload.get("sub")
    if not subject:
        raise JwtValidationError("Token missing subject")

    roles = _roles_from_payload(payload)
    email = payload.get("email")
    return Principal(subject=str(subject), roles=roles, email=str(email) if email else None)


async def warm_jwks_cache(settings: Settings | None = None) -> None:
    """Optional startup warm-up when OIDC is enabled."""
    settings = settings or get_settings()
    if not settings.oidc_enabled or settings.oidc_jwks_json:
        return
    url = _jwks_url(settings)
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.get(url)
