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
    assert viewer.can("run:read")
    assert not viewer.can("workflow:write")
    assert auth.DEV_USER.can("workflow:delete")


class _Keys:
    def __init__(self, public_key) -> None:
        self.key = public_key

    def get_signing_key_from_jwt(self, _token: str):
        return self


@pytest.fixture
def fresh_settings():
    """Settings read again from the (patched) environment, and reset even if the test fails."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_user_from_token(monkeypatch, fresh_settings):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", "http://kc.test/realms/repody")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER_ALIASES", "http://localhost/realms/repody")
    monkeypatch.setattr(auth, "_jwks", lambda _url: _Keys(private.public_key()))

    def token(issuer: str, **claims) -> str:
        payload = {
            "sub": "alice",
            "iss": issuer,
            "typ": "Bearer",
            "exp": int(time.time()) + 60,
            **claims,
        }
        return jwt.encode(payload, private, algorithm="RS256")

    user = auth.user_from_token(
        token(
            "http://localhost/realms/repody",
            realm_access={"roles": ["operator", "other"]},
            groups=["/viewer"],
        )
    )
    assert user.subject == "alice"
    assert user.roles == {"operator", "viewer"}
    assert user.client is None
    assert user.account is None  # a single-client installation: sees everything

    # A client company is a Keycloak group (full path or not); its users see only its work.
    client_user = auth.user_from_token(
        token(
            "http://kc.test/realms/repody",
            realm_access={"roles": ["operator"]},
            groups=["/clients/Client-Acme"],
        )
    )
    assert client_user.account == "client-acme"
    admin = auth.User(subject="p", roles=frozenset({"platform_admin"}), client="client-acme")
    assert admin.account is None  # a platform admin sees every client
    assert admin.can("credits:grant")
    assert not client_user.can("credits:grant")
    with pytest.raises(auth.InvalidTokenError):
        auth.user_from_token(token("http://evil.test"))
    with pytest.raises(auth.InvalidTokenError):
        auth.user_from_token("not-a-jwt")
    with pytest.raises(auth.InvalidTokenError, match="Not an access token"):
        auth.user_from_token(token("http://localhost/realms/repody", typ="ID"))


def test_uvicorn_logs_go_through_the_json_formatter():
    import logging

    from repody.infra import observability

    logging.getLogger("uvicorn.access").addHandler(logging.StreamHandler())
    observability.setup()
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        assert logging.getLogger(name).handlers == []
        assert logging.getLogger(name).propagate


async def test_scale_to_zero_model_server_is_not_probed(monkeypatch, fresh_settings):
    """The platform page does not ask an endpoint that scales to zero whether it is up: the
    question would start it (and bill it)."""
    from repody.extraction import client

    monkeypatch.setenv("AUDIT_LLAMACPP_PROBE", "false")
    assert await client.model_available() is None
