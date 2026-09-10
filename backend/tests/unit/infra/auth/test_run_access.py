"""Unit tests for run enqueue access policy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from repody.infra.auth.principal import Principal
from repody.infra.auth.run_access import resolve_owner_subject, resolve_run_enqueue_source
from repody.runtime.contracts.result import ErrorCode
from repody.settings import Settings


def _settings(**kwargs: object) -> Settings:
    if kwargs.get("oidc_enabled") is True and "oidc_issuer" not in kwargs:
        kwargs["oidc_issuer"] = "https://auth.example.com/realms/repody"
    return Settings(_env_file=None, **kwargs)  # type: ignore[arg-type]


def _workflow(*, deployed: bool = True, api_key: str = "hashed") -> SimpleNamespace:
    return SimpleNamespace(
        id="wf1",
        deployed_at=object() if deployed else None,
        api_key=api_key,
    )


def test_resolve_owner_subject_dev_mode():
    settings = _settings(oidc_enabled=False)
    assert resolve_owner_subject(None, settings=settings) == "dev-local"
    assert resolve_owner_subject("Bearer x", settings=settings) == "dev-local"


def test_resolve_owner_subject_oidc_missing_token():
    settings = _settings(oidc_enabled=True, oidc_issuer="https://auth.example/realms/r")
    assert resolve_owner_subject(None, settings=settings) is None


@pytest.mark.asyncio
async def test_resolve_run_enqueue_missing_workflow():
    session = MagicMock()
    with patch("repody.infra.auth.run_access.load_workflow", new=AsyncMock(return_value=None)):
        result = await resolve_run_enqueue_source(session, "missing", None)
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_resolve_run_enqueue_api_key_when_deployed():
    session = MagicMock()
    wf = _workflow(deployed=True)
    with (
        patch("repody.infra.auth.run_access.load_workflow", new=AsyncMock(return_value=wf)),
        patch("repody.infra.auth.run_access.verify_api_key", return_value=True),
        patch(
            "repody.infra.auth.run_access.get_settings", return_value=_settings(oidc_enabled=True)
        ),
    ):
        result = await resolve_run_enqueue_source(session, "wf1", "Bearer secret-key")
    assert result.is_ok
    assert result.unwrap()[0] == "api"


@pytest.mark.asyncio
async def test_resolve_run_enqueue_oidc_operator_test_run():
    session = MagicMock()
    wf = _workflow(deployed=False)
    principal = Principal(subject="user-1", roles=("operator",))
    with (
        patch("repody.infra.auth.run_access.load_workflow", new=AsyncMock(return_value=wf)),
        patch("repody.infra.auth.run_access.verify_api_key", return_value=False),
        patch(
            "repody.infra.auth.run_access.get_settings", return_value=_settings(oidc_enabled=True)
        ),
        patch("repody.infra.auth.run_access.principal_from_bearer", return_value=principal),
        patch("repody.infra.auth.run_access.authorize", return_value=True),
    ):
        result = await resolve_run_enqueue_source(session, "wf1", "Bearer jwt")
    assert result.is_ok
    assert result.unwrap()[0] == "test"


@pytest.mark.asyncio
async def test_resolve_run_enqueue_oidc_forbidden_without_execute():
    session = MagicMock()
    wf = _workflow(deployed=False)
    principal = Principal(subject="user-1", roles=("viewer",))
    with (
        patch("repody.infra.auth.run_access.load_workflow", new=AsyncMock(return_value=wf)),
        patch("repody.infra.auth.run_access.verify_api_key", return_value=False),
        patch(
            "repody.infra.auth.run_access.get_settings", return_value=_settings(oidc_enabled=True)
        ),
        patch("repody.infra.auth.run_access.principal_from_bearer", return_value=principal),
        patch("repody.infra.auth.run_access.authorize", return_value=False),
    ):
        result = await resolve_run_enqueue_source(session, "wf1", "Bearer jwt")
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code == ErrorCode.FORBIDDEN


@pytest.mark.asyncio
async def test_resolve_run_enqueue_oidc_missing_bearer():
    session = MagicMock()
    wf = _workflow(deployed=False)
    with (
        patch("repody.infra.auth.run_access.load_workflow", new=AsyncMock(return_value=wf)),
        patch(
            "repody.infra.auth.run_access.get_settings", return_value=_settings(oidc_enabled=True)
        ),
    ):
        result = await resolve_run_enqueue_source(session, "wf1", None)
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code == ErrorCode.UNAUTHORIZED


@pytest.mark.asyncio
async def test_resolve_run_enqueue_dev_mode_allows_test_without_token():
    session = MagicMock()
    wf = _workflow(deployed=False)
    with (
        patch("repody.infra.auth.run_access.load_workflow", new=AsyncMock(return_value=wf)),
        patch(
            "repody.infra.auth.run_access.get_settings", return_value=_settings(oidc_enabled=False)
        ),
    ):
        result = await resolve_run_enqueue_source(session, "wf1", None)
    assert result.is_ok
    assert result.unwrap()[0] == "test"
