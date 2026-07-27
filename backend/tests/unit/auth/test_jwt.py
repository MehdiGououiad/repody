import pytest

from audit_workbench.auth.jwt_validator import JwtValidationError, principal_from_bearer
from audit_workbench.settings import Settings, clear_settings_cache
from tests.helpers.oidc_tokens import TEST_ISSUER, jwks_json_for_tests, mint_access_token


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch: pytest.MonkeyPatch):
    clear_settings_cache()
    monkeypatch.setenv("AUDIT_OIDC_AUDIENCE", "")
    monkeypatch.setenv("AUDIT_OIDC_JWKS_URL", "")
    yield
    clear_settings_cache()


def test_principal_from_bearer_extracts_roles() -> None:
    settings = Settings(
        oidc_enabled=True,
        oidc_issuer=TEST_ISSUER,
        oidc_jwks_json=jwks_json_for_tests(),
    )
    token = mint_access_token(roles=["admin"])
    principal = principal_from_bearer(token, settings)
    assert principal.subject == "test-user"
    assert "admin" in principal.roles


def test_principal_rejects_missing_token() -> None:
    settings = Settings(
        oidc_enabled=True,
        oidc_issuer=TEST_ISSUER,
        oidc_jwks_json=jwks_json_for_tests(),
    )
    with pytest.raises(JwtValidationError):
        principal_from_bearer(None, settings)


def test_principal_accepts_configured_audience() -> None:
    settings = Settings(
        oidc_enabled=True,
        oidc_issuer=TEST_ISSUER,
        oidc_audience="repody-api",
        oidc_jwks_json=jwks_json_for_tests(),
    )
    token = mint_access_token(roles=["operator"], audience="repody-api")
    principal = principal_from_bearer(token, settings)
    assert principal.subject == "test-user"


def test_principal_rejects_wrong_audience() -> None:
    settings = Settings(
        oidc_enabled=True,
        oidc_issuer=TEST_ISSUER,
        oidc_audience="repody-api",
        oidc_jwks_json=jwks_json_for_tests(),
    )
    token = mint_access_token(roles=["operator"], audience="other-client")
    with pytest.raises(JwtValidationError):
        principal_from_bearer(token, settings)


def test_principal_ignores_audience_when_not_configured() -> None:
    settings = Settings(
        oidc_enabled=True,
        oidc_issuer=TEST_ISSUER,
        oidc_jwks_json=jwks_json_for_tests(),
    )
    token = mint_access_token(roles=["operator"], audience="other-client")
    principal = principal_from_bearer(token, settings)
    assert principal.subject == "test-user"
