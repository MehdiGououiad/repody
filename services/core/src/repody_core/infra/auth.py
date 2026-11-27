"""Caller identity and RBAC for ``repody_core`` (Keycloak RS256 JWKS)."""

from dataclasses import dataclass
from functools import lru_cache

import jwt

from repody_core.settings import get_settings

CORE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"case:read", "approval:read", "audit:read"}),
    "operator": frozenset(
        {
            "case:read",
            "case:write",
            "approval:read",
            "approval:make",
            "audit:read",
        }
    ),
    "checker": frozenset(
        {
            "case:read",
            "approval:read",
            "approval:check",
            "audit:read",
        }
    ),
    "admin": frozenset(
        {
            "case:read",
            "case:write",
            "approval:read",
            "approval:make",
            "approval:check",
            "audit:read",
            "audit:verify",
        }
    ),
    "platform_admin": frozenset(
        {
            "case:read",
            "case:write",
            "approval:read",
            "approval:make",
            "approval:check",
            "audit:read",
            "audit:verify",
        }
    ),
}

CLIENT_GROUP_PREFIX = "client-"


@dataclass(frozen=True, slots=True)
class CoreUser:
    """Authenticated caller identity."""

    subject: str
    roles: frozenset[str]
    client: str | None = None

    def can(self, permission: str) -> bool:
        """Whether any of the caller's roles grants ``permission``."""
        return any(permission in CORE_PERMISSIONS.get(role, ()) for role in self.roles)

    @property
    def account(self) -> str | None:
        """Tenant account scope (None for platform admins)."""
        if "platform_admin" in self.roles:
            return None
        return self.client


DEV_USER = CoreUser(subject="dev-local", roles=frozenset({"platform_admin"}))


class InvalidTokenError(Exception):
    """Raised when a bearer token fails verification."""


@lru_cache
def _jwks(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, timeout=5)


def user_from_token(token: str) -> CoreUser:
    """Verify a Keycloak RS256 bearer access token against JWKS."""
    settings = get_settings()
    issuer = (settings.oidc_issuer or "").rstrip("/")
    jwks_url = settings.oidc_jwks_url or f"{issuer}/protocol/openid-connect/certs"
    try:
        key = _jwks(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=settings.oidc_audience,
            options={"verify_aud": bool(settings.oidc_audience), "require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if claims.get("typ") != "Bearer":
        raise InvalidTokenError("Not an access token.")
    roles = (
        frozenset((claims.get("realm_access") or {}).get("roles") or ()) & CORE_PERMISSIONS.keys()
    )
    groups = {str(group).strip("/").rsplit("/", 1)[-1] for group in claims.get("groups") or []}
    clients = sorted(
        name
        for name in (g.lower() for g in groups)
        if name.startswith(CLIENT_GROUP_PREFIX) and len(name) > len(CLIENT_GROUP_PREFIX)
    )
    return CoreUser(subject=str(claims["sub"]), roles=roles, client=clients[0] if clients else None)
