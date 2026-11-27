"""Caller identity and RBAC for ``repody_fraud`` (Keycloak RS256 JWKS)."""

from dataclasses import dataclass
from functools import lru_cache

import jwt

from repody_fraud.settings import get_settings

FRAUD_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"fraud:read"}),
    "operator": frozenset({"fraud:read", "fraud:write"}),
    "checker": frozenset({"fraud:read"}),
    "admin": frozenset({"fraud:read", "fraud:write"}),
    "platform_admin": frozenset({"fraud:read", "fraud:write"}),
}

CLIENT_GROUP_PREFIX = "client-"


@dataclass(frozen=True, slots=True)
class FraudUser:
    """Authenticated caller identity."""

    subject: str
    roles: frozenset[str]
    client: str | None = None

    def can(self, permission: str) -> bool:
        return any(permission in FRAUD_PERMISSIONS.get(role, ()) for role in self.roles)

    @property
    def account(self) -> str | None:
        if "platform_admin" in self.roles:
            return None
        return self.client


DEV_USER = FraudUser(subject="dev-local", roles=frozenset({"platform_admin"}))


class InvalidTokenError(Exception):
    """Raised when a bearer token fails verification."""


@lru_cache
def _jwks(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, timeout=5)


def user_from_token(token: str) -> FraudUser:
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
        frozenset((claims.get("realm_access") or {}).get("roles") or ()) & FRAUD_PERMISSIONS.keys()
    )
    groups = {str(group).strip("/").rsplit("/", 1)[-1] for group in claims.get("groups") or []}
    clients = sorted(
        name
        for name in (g.lower() for g in groups)
        if name.startswith(CLIENT_GROUP_PREFIX) and len(name) > len(CLIENT_GROUP_PREFIX)
    )
    return FraudUser(
        subject=str(claims["sub"]), roles=roles, client=clients[0] if clients else None
    )
