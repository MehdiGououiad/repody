import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr, ValidationError

from repody.infra import auth
from repody.settings import Settings, get_settings


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_production_and_staging_require_oidc(environment):
    with pytest.raises(ValidationError, match="OIDC"):
        Settings(deployment_environment=environment, oidc_enabled=False)


def test_a_public_access_request_form_needs_turnstile_in_production():
    live = {
        "deployment_environment": "production",
        "oidc_enabled": True,
        "oidc_issuer": "https://auth.test/realms/repody",
        "oidc_audience": "repody-api",
        "access_requests_enabled": True,
    }
    with pytest.raises(ValidationError, match="TURNSTILE"):
        Settings(**live, turnstile_secret=SecretStr(""))
    assert Settings(**live, turnstile_secret=SecretStr("s3cret")).access_requests_enabled


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
    assert user.roles == {"operator"}  # a group is never a role, even one named like a role
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
    escalated = auth.user_from_token(
        token("http://kc.test/realms/repody", groups=["/platform_admin", "/client-acme"])
    )
    assert escalated.roles == frozenset()
    assert escalated.account == "client-acme"

    # A multi-client installation: outside every company, a user has no permission at all.
    monkeypatch.setenv("AUDIT_REQUIRE_CLIENT_GROUP", "true")
    get_settings.cache_clear()
    stray = auth.user_from_token(
        token("http://kc.test/realms/repody", realm_access={"roles": ["admin"]})
    )
    assert stray.roles == frozenset()
    assert not stray.can("run:read")
    assert client_user.can("run:read")
    platform = auth.user_from_token(
        token("http://kc.test/realms/repody", realm_access={"roles": ["platform_admin"]})
    )
    assert platform.can("clients:manage")
    with pytest.raises(auth.InvalidTokenError):
        auth.user_from_token(token("http://evil.test"))
    with pytest.raises(auth.InvalidTokenError):
        auth.user_from_token("not-a-jwt")
    with pytest.raises(auth.InvalidTokenError, match="Not an access token"):
        auth.user_from_token(token("http://localhost/realms/repody", typ="ID"))


def test_uvicorn_logs_are_written_once_as_json_without_health_checks(capsys):
    import json
    import logging

    from repody.infra import observability

    access = logging.getLogger("uvicorn.access")
    access.disabled = False  # alembic.ini's fileConfig, run in-process by another test, disables it
    access.addHandler(logging.StreamHandler())  # as uvicorn does
    observability.setup()
    # Uvicorn's access line: client, method, path, HTTP version, status.
    line = '%s - "%s %s HTTP/%s" %d'
    access.info(line, "10.0.0.1:1", "GET", "/v1/workflows", "1.1", 200)
    access.info(line, "127.0.0.1:2", "GET", "/v1/healthz", "1.1", 200)  # Docker's health check
    access.info(line, "127.0.0.1:3", "GET", "/v1/healthz", "1.1", 503)
    lines = capsys.readouterr().err.splitlines()
    assert [json.loads(line)["event"] for line in lines] == [
        '10.0.0.1:1 - "GET /v1/workflows HTTP/1.1" 200',
        '127.0.0.1:3 - "GET /v1/healthz HTTP/1.1" 503',
    ]


def test_with_tracing_on_each_log_line_names_its_trace(monkeypatch, capsys):
    import json
    import logging

    from opentelemetry import trace

    from repody.infra import observability

    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setattr(observability, "_trace_hatchet", lambda: None)
    observability.setup()
    span = trace.NonRecordingSpan(trace.SpanContext(trace_id=0xABC, span_id=0xDEF, is_remote=False))
    with trace.use_span(span):
        logging.getLogger("repody.test").info("inside")
    logging.getLogger("repody.test").info("outside")
    lines = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert lines[0]["trace_id"] == "00000000000000000000000000000abc"
    assert "trace_id" not in lines[1]


async def test_scale_to_zero_model_server_is_not_probed(monkeypatch, fresh_settings):
    """The platform page does not ask an endpoint that scales to zero whether it is up: the
    question would start it (and bill it)."""
    from repody.extraction import client

    monkeypatch.setenv("AUDIT_INFERENCE_PROBE", "false")
    assert await client.model_available() is None
