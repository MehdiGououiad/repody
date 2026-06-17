import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from audit_workbench.auth.dependencies import get_current_principal, require_permission
from audit_workbench.settings import clear_settings_cache
from tests.helpers.oidc_tokens import TEST_ISSUER, jwks_json_for_tests, mint_access_token


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch: pytest.MonkeyPatch):
    clear_settings_cache()
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("AUDIT_OIDC_JWKS_JSON", jwks_json_for_tests())
    yield
    clear_settings_cache()


def test_require_permission_blocks_viewer_write() -> None:
    app = FastAPI()

    @app.get("/secure", dependencies=[Depends(require_permission("workflow", "write"))])
    async def secure(principal=Depends(get_current_principal)):
        return {"subject": principal.subject}

    client = TestClient(app)
    viewer_token = mint_access_token(roles=["viewer"])
    res = client.get("/secure", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403

    operator_token = mint_access_token(roles=["operator"])
    ok = client.get("/secure", headers={"Authorization": f"Bearer {operator_token}"})
    assert ok.status_code == 200
