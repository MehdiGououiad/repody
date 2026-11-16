"""Who is calling: Keycloak users (JWT, verified with PyJWT against the realm JWKS) and
workflow API keys (stored as SHA-256 hashes)."""

import hashlib
import secrets
from dataclasses import dataclass
from functools import lru_cache

import jwt

from repody.schemas.platform import PERMISSIONS, Access, Permission
from repody.settings import get_settings

_VIEWER: frozenset[str] = frozenset({"workflow:read", "run:read"})
_OPERATOR = _VIEWER | {"workflow:write", "workflow:deploy", "run:execute", "metrics:read"}
_ADMIN = _OPERATOR | {"workflow:delete"}
_PLATFORM_ADMIN = _ADMIN | {"credits:grant", "clients:manage"}
# The playground's anonymous visitor: builds and deletes its own workflows, reads the examples,
# never runs or publishes (both cost model time: the API answers 402, contact us for credits).
_DEMO_VISITOR = _VIEWER | {"workflow:write", "workflow:delete", "metrics:read"}
DEMO_VISITOR_ROLE = "demo_visitor"
# What a playground visitor is offered but cannot do: both cost model time (402).
PAID_PERMISSIONS: tuple[Permission, ...] = ("workflow:deploy", "run:execute")
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": _VIEWER,
    "operator": _OPERATOR,
    "admin": _ADMIN,
    "platform_admin": _PLATFORM_ADMIN,
    DEMO_VISITOR_ROLE: _DEMO_VISITOR,
}


@dataclass(frozen=True, slots=True)
class User:
    subject: str
    roles: frozenset[str]
    # The client company the user belongs to (its Keycloak group, ``client-<name>``): they see
    # and change only its workflows and runs, and its credits pay for their runs.
    client: str | None = None

    def can(self, permission: Permission) -> bool:
        return any(permission in ROLE_PERMISSIONS.get(role, ()) for role in self.roles)

    def access(self) -> Access:
        granted: list[Permission] = [p for p in PERMISSIONS if self.can(p)]
        paid: list[Permission] = (
            [p for p in PAID_PERMISSIONS if p not in granted] if self.visitor else []
        )
        return Access(roles=sorted(self.roles), permissions=granted, with_credits=paid)

    @property
    def visitor(self) -> str | None:
        """The playground visitor id (demo mode), whose workflows this user sees; else None."""
        return self.subject if DEMO_VISITOR_ROLE in self.roles else None

    @property
    def account(self) -> str | None:
        """Whose workflows and runs this user sees and changes (repody.app.scope): their client
        company or, in the playground, their own; None (everything) for a platform admin and for
        users outside any client (a single-client installation)."""
        if self.visitor:
            return self.visitor
        if "platform_admin" in self.roles:
            return None
        return self.client


DEV_USER = User(subject="dev-local", roles=frozenset({"platform_admin"}))
CLIENT_GROUP_PREFIX = "client-"


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
    groups = {str(group).strip("/").rsplit("/", 1)[-1] for group in claims.get("groups") or []}
    roles |= groups
    # Only demo mode makes visitors (repody.api.deps); a token cannot claim that role.
    signed_in_roles = ROLE_PERMISSIONS.keys() - {DEMO_VISITOR_ROLE}
    # One client per user; a user put in several by mistake gets the first by name.
    clients = sorted(
        name
        for name in (g.lower() for g in groups)
        if name.startswith(CLIENT_GROUP_PREFIX) and len(name) > len(CLIENT_GROUP_PREFIX)
    )
    return User(
        subject=str(claims["sub"]),
        roles=frozenset(roles) & signed_in_roles,
        client=clients[0] if clients else None,
    )


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def api_key_matches(key: str, stored_hash: str | None) -> bool:
    return stored_hash is not None and secrets.compare_digest(hash_api_key(key), stored_hash)


def new_api_key() -> str:
    """A workflow API key; only its hash and hint are stored, the key is shown once."""
    return f"wbk_live_{secrets.token_hex(16)}"


def api_key_hint(key: str) -> str:
    return f"{key[:12]}********"
