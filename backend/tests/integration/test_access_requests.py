"""Access requests: the site's public form (limits, anti-robot check) and the admin's approve and
decline, which create the client, invite the person and give credits."""

import pytest
from httpx import ASGITransport, AsyncClient

from repody.infra import turnstile
from repody.main import create_app
from repody.settings import get_settings
from tests.integration.test_admin import CLIENT_ADMIN, PLATFORM, as_user, kc  # noqa: F401

FORM = {
    "name": "Nadia Benali",
    "email": "Nadia@Bank.test",
    "company": "Bank of Test",
    "sector": "Banking",
    "message": "KYC files",
    "locale": "fr",
    "consent": True,
    "turnstileToken": "token",
}
SITE = "https://repody.com"


async def anonymous_post(api: AsyncClient, body: dict, ip: str = "203.0.113.7"):
    return await api.post("/v1/access-requests", json=body, headers={"CF-Connecting-IP": ip})


async def test_a_prospect_asks_and_the_admin_approves(api, as_user, kc):  # noqa: F811
    assert (await anonymous_post(api, FORM)).status_code == 202
    platform = as_user(PLATFORM)
    [request] = (await platform.get("/v1/admin/requests")).json()
    assert request["email"] == "nadia@bank.test"
    assert request["status"] == "new"

    approved = await platform.post(
        f"/v1/admin/requests/{request['id']}/approve",
        json={"slug": "bank-of-test", "role": "admin", "credits": 200},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["request"]["status"] == "approved"
    assert body["request"]["account"] == "client-bank-of-test"
    assert body["invited"]["user"]["email"] == "nadia@bank.test"
    assert body["invited"]["temporaryPassword"]
    client = (await platform.get("/v1/admin/clients/client-bank-of-test")).json()
    assert client["summary"]["balance"] == 200
    assert client["users"][0]["firstName"] == "Nadia"
    actions = [e["action"] for e in (await platform.get("/v1/admin/events")).json()]
    assert actions[0] == "request.approved"
    again = await platform.post(
        f"/v1/admin/requests/{request['id']}/approve", json={"slug": "bank-of-test"}
    )
    assert again.status_code == 409


async def test_a_request_is_declined_with_a_note(api, as_user, kc):  # noqa: F811
    await anonymous_post(api, FORM)
    platform = as_user(PLATFORM)
    [request] = (await platform.get("/v1/admin/requests")).json()
    declined = await platform.post(
        f"/v1/admin/requests/{request['id']}/decline", json={"note": "Not a fit yet"}
    )
    assert declined.json()["status"] == "declined"
    assert declined.json()["note"] == "Not a fit yet"
    assert (await platform.get("/v1/admin/requests", params={"status": "new"})).json() == []


async def test_one_network_sends_a_limited_number(api, monkeypatch):
    monkeypatch.setattr(get_settings(), "access_requests_per_hour", 2)
    for n in range(2):
        body = {**FORM, "email": f"p{n}@x.test"}
        assert (await anonymous_post(api, body)).status_code == 202
    assert (await anonymous_post(api, {**FORM, "email": "p9@x.test"})).status_code == 429
    other_network = await anonymous_post(api, {**FORM, "email": "p9@x.test"}, ip="198.51.100.1")
    assert other_network.status_code == 202


async def test_a_second_request_from_a_waiting_email_is_merged(api, as_user, kc):  # noqa: F811
    await anonymous_post(api, FORM)
    await anonymous_post(api, {**FORM, "message": "Also invoices"})
    [request] = (await as_user(PLATFORM).get("/v1/admin/requests")).json()
    assert request["message"] == "KYC files\n\nAlso invoices"


async def test_the_form_needs_consent_and_passes_the_robot_check(api, monkeypatch):
    assert (await anonymous_post(api, {**FORM, "consent": False})).status_code == 422

    async def refuse(_token: str, _ip: str | None) -> bool:
        return False

    monkeypatch.setattr(turnstile, "verify", refuse)
    refused = await anonymous_post(api, FORM)
    assert refused.status_code == 400
    assert "anti-robot" in refused.json()["detail"]


async def test_only_platform_admins_see_and_decide_requests(api, as_user, kc):  # noqa: F811
    client_admin = as_user(CLIENT_ADMIN)
    assert (await client_admin.get("/v1/admin/requests")).status_code == 403
    assert (
        await client_admin.post("/v1/admin/requests/req-x/approve", json={"slug": "a"})
    ).status_code == 403
    nobody = as_user(None)
    assert (await nobody.get("/v1/admin/requests")).status_code == 401


async def test_the_site_may_post_across_origins(api, monkeypatch):
    monkeypatch.setattr(get_settings(), "cors_origins", [SITE])
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        preflight = await client.options(
            "/v1/access-requests",
            headers={
                "Origin": SITE,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.headers["access-control-allow-origin"] == SITE
        other = await client.options(
            "/v1/access-requests",
            headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "POST"},
        )
        assert "access-control-allow-origin" not in other.headers


@pytest.fixture(autouse=True)
def _no_turnstile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "turnstile_secret", None)


async def _request_id(as_user) -> str:  # noqa: F811
    return (await as_user(PLATFORM).get("/v1/admin/requests")).json()[0]["id"]


async def test_someone_keycloak_knows_joins_the_client(api, as_user, kc):  # noqa: F811
    """A person who signed up before (no client any more) is joined, with a fresh password."""
    known = await kc.create_user(email="nadia@bank.test", first_name="N", last_name="")
    await anonymous_post(api, FORM)
    platform = as_user(PLATFORM)
    approved = await platform.post(
        f"/v1/admin/requests/{await _request_id(as_user)}/approve", json={"slug": "bank"}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["invited"]["user"]["id"] == known
    assert kc.passwords[known]
    assert len(kc.users) == 1  # no second account


async def test_an_email_of_another_client_or_an_admin_is_refused(api, as_user, kc):  # noqa: F811
    other = await kc.create_group("client-other")
    user = await kc.create_user(email="nadia@bank.test", first_name="N", last_name="")
    await kc.join(user, other.id)
    await anonymous_post(api, FORM)
    platform = as_user(PLATFORM)
    path = f"/v1/admin/requests/{await _request_id(as_user)}/approve"
    refused = await platform.post(path, json={"slug": "bank"})
    assert refused.status_code == 409
    assert "client-other" in refused.json()["detail"]
    await kc.leave(user, other.id)
    kc.users[user]["roles"].add("platform_admin")
    refused = await platform.post(path, json={"slug": "bank"})
    assert refused.status_code == 409
    assert "platform admin" in refused.json()["detail"]


async def test_a_retried_approval_does_not_invite_or_credit_twice(api, as_user, kc, monkeypatch):  # noqa: F811
    await anonymous_post(api, FORM)
    platform = as_user(PLATFORM)
    request_id = await _request_id(as_user)
    calls = {"n": 0}
    from repody.app import admin

    real_grant = admin.grant

    async def failing_grant(*_args, **_kwargs):
        calls["n"] += 1
        raise RuntimeError("database went away")

    monkeypatch.setattr(admin, "grant", failing_grant)
    with pytest.raises(RuntimeError):
        await platform.post(f"/v1/admin/requests/{request_id}/approve", json={"slug": "bank"})
    monkeypatch.setattr(admin, "grant", real_grant)
    retried = await platform.post(f"/v1/admin/requests/{request_id}/approve", json={"slug": "bank"})
    assert retried.status_code == 200, retried.text
    assert len(kc.users) == 1
    detail = (await platform.get("/v1/admin/clients/client-bank")).json()
    assert detail["summary"]["balance"] == 200
    assert calls["n"] == 1


async def test_declined_requests_are_deleted_after_their_retention(api, as_user, kc):  # noqa: F811
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from repody.app.access import purge_declined
    from repody.infra import db
    from repody.infra.models import AccessRequest

    await anonymous_post(api, FORM)
    platform = as_user(PLATFORM)
    request_id = await _request_id(as_user)
    await platform.post(f"/v1/admin/requests/{request_id}/decline", json={"note": ""})
    async with db.session_factory() as session:
        assert await purge_declined(session) == 0
        await session.execute(
            update(AccessRequest).values(decided_at=datetime.now(UTC) - timedelta(days=91))
        )
        assert await purge_declined(session) == 1
        await session.commit()
