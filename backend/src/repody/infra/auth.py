"""Who is calling: Keycloak users (JWT, verified with PyJWT against the realm JWKS) and
workflow API keys (stored as SHA-256 hashes)."""

import hashlib
import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import jwt

from repody.settings import get_settings

Permission = Literal[
    "workflow:read", "workflow:write", "workflow:delete", "run:read", "run:execute", "metrics:read"
]

_VIEWER: frozenset[str] = frozenset({"workflow:read", "run:read"})
_OPERATOR = _VIEWER | {"workflow:write", "run:execute", "metrics:read"}
_ADMIN = _OPERATOR | {"workflow:delete"}
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": _VIEWER,
    "operator": _OPERATOR,
    "admin": _ADMIN,
    "platform_admin": _ADMIN,
}


@dataclass(frozen=True, slots=True)
class User:
    subject: str
    roles: frozenset[str]

    def can(self, permission: Permission) -> bool:
        return any(permission in ROLE_PERMISSIONS.get(role, ()) for role in self.roles)


DEV_USER = User(subject="dev-local", roles=frozenset({"platform_admin"}))


class InvalidTokenError(Exception):
    pass


# A Keycloak outage fails a request in seconds, not after PyJWT's default 30 s.
JWKS_TIMEOUT_SECONDS = 5


@lru_cache
def _jwks(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, timeout=JWKS_TIMEOUT_SECONDS)


def user_from_token(token: str) -> User:
    """Verify a Keycloak access token (not an ID or refresh token: ``typ`` is Bearer) for the
    configured audience; roles come from realm roles and groups."""
    settings = get_settings()
    issuer = (settings.oidc_issuer or "").rstrip("/")
    jwks_url = settings.oidc_jwks_url or f"{issuer}/protocol/openid-connect/certs"
    try:
        key = _jwks(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=[issuer, *(alias.rstrip("/") for alias in settings.oidc_issuer_aliases)],
            audience=settings.oidc_audience,
            options={"verify_aud": bool(settings.oidc_audience), "require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if claims.get("typ") != "Bearer":
        raise InvalidTokenError("Not an access token.")
    roles = {*((claims.get("realm_access") or {}).get("roles") or [])}
    roles |= {str(group).lstrip("/") for group in claims.get("groups") or []}
    return User(subject=str(claims["sub"]), roles=frozenset(roles) & ROLE_PERMISSIONS.keys())


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def api_key_matches(key: str, stored_hash: str | None) -> bool:
    return stored_hash is not None and secrets.compare_digest(hash_api_key(key), stored_hash)


def new_api_key() -> str:
    """A workflow API key; only its hash and hint are stored, the key is shown once."""
    return f"wbk_live_{secrets.token_hex(16)}"


def api_key_hint(key: str) -> str:
    return f"{key[:12]}********"
