"""The Keycloak admin client against a scripted Keycloak (httpx MockTransport)."""

import json

import httpx
import pytest
from pydantic import SecretStr

from repody.infra.keycloak_admin import KeycloakAdmin, KeycloakError
from repody.settings import get_settings

ISSUER = "http://keycloak:8080/realms/repody"
ADMIN = "http://keycloak:8080/admin/realms/repody"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "keycloak_internal_issuer", ISSUER)
    monkeypatch.setattr(settings, "keycloak_admin_client_secret", SecretStr("s3cret"))
    return settings


def keycloak(handler) -> KeycloakAdmin:
    kc = KeycloakAdmin()
    kc._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return kc


async def test_it_signs_in_once_and_creates_a_user(settings):
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url).split("?")[0]))
        if request.url.path.endswith("/token"):
            form = dict(x.split("=") for x in request.content.decode().split("&"))
            assert form == {
                "grant_type": "client_credentials",
                "client_id": "repody-admin",
                "client_secret": "s3cret",
            }
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        assert request.headers["Authorization"] == "Bearer t"
        if request.method == "POST" and request.url.path.endswith("/users"):
            body = json.loads(request.content)
            assert body["requiredActions"] == ["UPDATE_PASSWORD"]
            return httpx.Response(201, headers={"Location": f"{ADMIN}/users/u-1"})
        return httpx.Response(204)

    kc = keycloak(handler)
    user_id = await kc.create_user(email="bob@acme.test", first_name="Bob", last_name="")
    await kc.set_temporary_password(user_id, "pw")
    assert user_id == "u-1"
    assert seen == [
        ("POST", f"{ISSUER}/protocol/openid-connect/token"),
        ("POST", f"{ADMIN}/users"),
        ("PUT", f"{ADMIN}/users/u-1/reset-password"),
    ]


async def test_keycloak_errors_become_clear_statuses(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return httpx.Response(409 if request.method == "POST" else 500)

    kc = keycloak(handler)
    with pytest.raises(KeycloakError) as conflict:
        await kc.create_user(email="bob@acme.test", first_name="", last_name="")
    assert conflict.value.status == 409
    with pytest.raises(KeycloakError) as broken:
        await kc.user("u-1")
    assert broken.value.status == 502


async def test_a_refused_admin_account_is_a_502(settings):
    kc = keycloak(lambda _request: httpx.Response(401, json={"error": "unauthorized_client"}))
    with pytest.raises(KeycloakError, match="refused"):
        await kc.groups("client-")
