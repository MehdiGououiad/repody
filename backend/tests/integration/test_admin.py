"""The admin area: clients and their users in Keycloak (a fake here), credits, workflows handed
to a client, spend, and the audit log of it all."""

import uuid
from collections.abc import AsyncIterator, Callable

import pytest
from httpx import ASGITransport, AsyncClient

from repody.api.deps import optional_user
from repody.infra import keycloak_admin
from repody.infra.auth import User
from repody.infra.keycloak_admin import KcGroup, KcUser, KeycloakError
from repody.main import create_app
from tests.files import FILE
from tests.integration.helpers import invoice_workflow

PLATFORM = User(subject="pat", roles=frozenset({"platform_admin"}))
CLIENT_ADMIN = User(subject="alice", roles=frozenset({"admin"}), client="client-acme")


class FakeKeycloak:
    def __init__(self) -> None:
        self.groups_: dict[str, KcGroup] = {}
        self.users: dict[str, dict] = {}
        self.passwords: dict[str, str] = {}

    async def groups(self, prefix: str) -> list[KcGroup]:
        return [g for g in self.groups_.values() if g.name.startswith(prefix)]

    async def group(self, name: str) -> KcGroup | None:
        return next((g for g in self.groups_.values() if g.name == name), None)

    async def create_group(self, name: str) -> KcGroup:
        group = KcGroup(id=str(uuid.uuid4()), name=name)
        self.groups_[group.id] = group
        return group

    def _kc_user(self, user_id: str) -> KcUser:
        u = self.users[user_id]
        return KcUser(
            id=user_id,
            email=u["email"],
            first_name=u["first"],
            last_name=u["last"],
            enabled=u["enabled"],
            created_ms=1_700_000_000_000,
            realm_roles=frozenset(u["roles"]),
        )

    async def members(self, group_id: str, *, roles: bool = True) -> list[KcUser]:
        return [self._kc_user(i) for i, u in self.users.items() if group_id in u["groups"]]

    async def user(self, user_id: str) -> KcUser:
        if user_id not in self.users:
            raise KeycloakError(404, "Not found in Keycloak.")
        return self._kc_user(user_id)

    async def user_groups(self, user_id: str) -> list[KcGroup]:
        return [self.groups_[g] for g in self.users[user_id]["groups"]]

    async def find_user(self, email: str) -> KcUser | None:
        found = [i for i, u in self.users.items() if u["email"] == email]
        return self._kc_user(found[0]) if found else None

    async def create_user(self, *, email: str, first_name: str, last_name: str) -> str:
        if any(u["email"] == email for u in self.users.values()):
            raise KeycloakError(409, "It already exists in Keycloak.")
        user_id = str(uuid.uuid4())
        self.users[user_id] = {
            "email": email,
            "first": first_name,
            "last": last_name,
            "enabled": True,
            "roles": set(),
            "groups": set(),
        }
        return user_id

    async def set_temporary_password(self, user_id: str, password: str) -> None:
        self.passwords[user_id] = password

    async def set_enabled(self, user_id: str, enabled: bool) -> None:
        self.users[user_id]["enabled"] = enabled

    async def join(self, user_id: str, group_id: str) -> None:
        self.users[user_id]["groups"].add(group_id)

    async def leave(self, user_id: str, group_id: str) -> None:
        self.users[user_id]["groups"].discard(group_id)

    async def set_role(self, user_id: str, role: str, managed: frozenset[str]) -> None:
        roles = self.users[user_id]["roles"]
        roles -= managed
        roles.add(role)


@pytest.fixture
def kc(monkeypatch: pytest.MonkeyPatch) -> FakeKeycloak:
    fake = FakeKeycloak()
    monkeypatch.setattr(keycloak_admin, "enabled", lambda: True)
    monkeypatch.setattr(keycloak_admin, "keycloak_admin", lambda: fake)
    return fake


@pytest.fixture
async def as_user(api: AsyncClient) -> AsyncIterator[Callable[[User | None], AsyncClient]]:
    clients: list[AsyncClient] = []

    def make(user: User | None) -> AsyncClient:
        app = create_app()
        app.dependency_overrides[optional_user] = lambda: user
        clients.append(AsyncClient(transport=ASGITransport(app=app), base_url="http://test"))
        return clients[-1]

    yield make
    for c in clients:
        await c.aclose()


async def test_an_admin_creates_a_client_invites_users_and_grants_credits(kc, as_user):
    platform = as_user(PLATFORM)
    created = await platform.post("/v1/admin/clients", json={"slug": "acme"})
    assert created.status_code == 201, created.text
    assert created.json()["account"] == "client-acme"
    assert (await platform.post("/v1/admin/clients", json={"slug": "acme"})).status_code == 409
    assert (await platform.post("/v1/admin/clients", json={"slug": "Acme Co"})).status_code == 422

    invited = await platform.post(
        "/v1/admin/clients/client-acme/users",
        json={"email": "Bob@Acme.test", "firstName": "Bob", "role": "operator"},
    )
    assert invited.status_code == 201, invited.text
    body = invited.json()
    user_id = body["user"]["id"]
    assert body["user"]["email"] == "bob@acme.test"
    assert body["user"]["role"] == "operator"
    assert body["temporaryPassword"] == kc.passwords[user_id]
    assert len(body["temporaryPassword"]) >= 12

    granted = await platform.post(
        "/v1/admin/clients/client-acme/credits", json={"amount": 200, "note": "trial"}
    )
    assert granted.json()["balance"] == 200

    detail = (await platform.get("/v1/admin/clients/client-acme")).json()
    assert detail["summary"]["balance"] == 200
    assert detail["summary"]["users"] == 1
    assert [u["email"] for u in detail["users"]] == ["bob@acme.test"]
    assert detail["ledger"][0]["kind"] == "grant"

    overview = (await platform.get("/v1/admin")).json()
    assert overview["enabled"] is True
    assert [c["account"] for c in overview["clients"]] == ["client-acme"]

    actions = [e["action"] for e in (await platform.get("/v1/admin/events")).json()]
    assert actions == ["credits.granted", "user.invited", "client.created"]


async def test_users_change_role_are_disabled_reset_and_removed(kc, as_user):
    platform = as_user(PLATFORM)
    await platform.post("/v1/admin/clients", json={"slug": "acme"})
    user_id = (
        await platform.post("/v1/admin/clients/client-acme/users", json={"email": "bob@acme.test"})
    ).json()["user"]["id"]
    path = f"/v1/admin/clients/client-acme/users/{user_id}"

    changed = await platform.patch(path, json={"role": "admin", "enabled": False})
    assert changed.json()["role"] == "admin"
    assert changed.json()["enabled"] is False
    assert kc.users[user_id]["roles"] == {"admin"}

    first = kc.passwords[user_id]
    reset = await platform.post(f"{path}/password")
    assert reset.json()["temporaryPassword"] != first

    # Another client's path does not reach this user.
    await platform.post("/v1/admin/clients", json={"slug": "globex"})
    other = f"/v1/admin/clients/client-globex/users/{user_id}"
    assert (await platform.patch(other, json={"role": "viewer"})).status_code == 404

    assert (await platform.delete(path)).status_code == 204
    assert kc.users[user_id]["groups"] == set()
    assert kc.users[user_id]["enabled"] is False


async def test_platform_admins_are_never_changed_from_the_admin_area(kc, as_user):
    platform = as_user(PLATFORM)
    await platform.post("/v1/admin/clients", json={"slug": "acme"})
    user_id = (
        await platform.post("/v1/admin/clients/client-acme/users", json={"email": "x@acme.test"})
    ).json()["user"]["id"]
    kc.users[user_id]["roles"].add("platform_admin")
    path = f"/v1/admin/clients/client-acme/users/{user_id}"
    assert (await platform.patch(path, json={"enabled": False})).status_code == 403
    assert (await platform.post(f"{path}/password")).status_code == 403
    # The role a client user may get is a client role, never platform_admin.
    invite = {"email": "y@acme.test", "role": "platform_admin"}
    response = await platform.post("/v1/admin/clients/client-acme/users", json=invite)
    assert response.status_code == 422


async def test_only_platform_admins_use_the_admin_area(kc, as_user):
    client_admin = as_user(CLIENT_ADMIN)
    for method, path in (
        ("GET", "/v1/admin"),
        ("POST", "/v1/admin/clients"),
        ("GET", "/v1/admin/events"),
        ("POST", "/v1/admin/clients/client-acme/credits"),
    ):
        assert (await client_admin.request(method, path, json={})).status_code == 403, path


async def test_a_workflow_is_handed_to_a_client(kc, as_user, api):
    platform, acme = as_user(PLATFORM), as_user(CLIENT_ADMIN)
    await platform.post("/v1/admin/clients", json={"slug": "acme"})
    await api.put("/v1/workflows/wf-prepared", json=invoice_workflow())  # shared
    assert (await acme.get("/v1/workflows/wf-prepared")).json()["readOnly"] is True

    handed = await platform.put(
        "/v1/admin/workflows/wf-prepared/account", json={"account": "client-acme"}
    )
    assert handed.json()["account"] == "client-acme"
    assert (await acme.get("/v1/workflows/wf-prepared")).json()["readOnly"] is False
    missing = await platform.put(
        "/v1/admin/workflows/wf-prepared/account", json={"account": "client-nobody"}
    )
    assert missing.status_code == 404
    listed = {w["id"]: w["account"] for w in (await platform.get("/v1/admin/workflows")).json()}
    assert listed["wf-prepared"] == "client-acme"


async def test_spend_counts_this_months_runs(kc, as_user, model_answer):
    platform, acme = as_user(PLATFORM), as_user(CLIENT_ADMIN)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    await acme.post("/v1/workflows/wf-acme/runs", files=FILE)
    spend = (await platform.get("/v1/admin")).json()["spend"]
    assert spend["runs"] == 1
    assert [a["account"] for a in spend["accounts"]] == ["client-acme"]
    assert spend["dollarsPerHour"] == 1.1


async def test_without_the_keycloak_account_the_area_says_how_to_set_it_up(as_user):
    platform = as_user(PLATFORM)
    overview = (await platform.get("/v1/admin")).json()
    assert overview["enabled"] is False
    response = await platform.post("/v1/admin/clients", json={"slug": "acme"})
    assert response.status_code == 503
    assert "repody-admin" in response.json()["detail"]
