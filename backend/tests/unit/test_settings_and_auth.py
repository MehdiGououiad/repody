import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from repody.infra import auth
from repody.settings import Settings, get_settings


def test_production_requires_oidc():
    with pytest.raises(ValidationError, match="OIDC"):
        Settings(deployment_environment="production", oidc_enabled=False)


def test_comma_separated_lists(monkeypatch):
    monkeypatch.setenv("AUDIT_CORS_ORIGINS", "http://a.test, http://b.test")
    assert Settings().cors_origins == ["http://a.test", "http://b.test"]


def test_api_keys():
    key = auth.new_api_key()
    assert auth.api_key_hint(key) == f"{key[:12]}********"
    assert auth.api_key_matches(key, auth.hash_api_key(key))
    assert not auth.api_key_matches("other", auth.hash_api_key(key))
    assert not auth.api_key_matches(key, None)


def test_roles():
    viewer = auth.User(subject="u", roles=frozenset({"viewer"}))
    assert viewer.can("run:read") and not viewer.can("workflow:write")
    assert auth.DEV_USER.can("workflow:delete")


class _Keys:
    def __init__(self, public_key) -> None:
        self.key = public_key

    def get_signing_key_from_jwt(self, _token: str):
        return self


def test_user_from_token(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", "http://kc.test/realms/repody")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER_ALIASES", "http://localhost/realms/repody")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_jwks", lambda _url: _Keys(private.public_key()))

    def token(issuer: str, **claims) -> str:
        payload = {"sub": "alice", "iss": issuer, "exp": int(time.time()) + 60, **claims}
        return jwt.encode(payload, private, algorithm="RS256")

    user = auth.user_from_token(
        token(
            "http://localhost/realms/repody",
            realm_access={"roles": ["operator", "other"]},
            groups=["/viewer"],
        )
    )
    assert user.subject == "alice" and user.roles == {"operator", "viewer"}
    with pytest.raises(auth.InvalidTokenError):
        auth.user_from_token(token("http://evil.test"))
    with pytest.raises(auth.InvalidTokenError):
        auth.user_from_token("not-a-jwt")
    get_settings.cache_clear()
