"""Tests for document model catalog service."""

from __future__ import annotations

import pytest

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.catalog.registry import parse_document_model
from audit_workbench.catalog import probes as catalog_probes
from audit_workbench.catalog.probes import (
    availability_for_spec,
    list_catalog_with_availability,
)


@pytest.mark.asyncio
async def test_list_catalog_marks_model_available_when_installed(monkeypatch):
    async def fake_installed(*args, **kwargs):
        settings = kwargs.get("settings") or args[0] if args else None
        from audit_workbench.settings import get_settings

        settings = settings or get_settings()
        model = settings.repody_vlm_model.lower()
        return {"docker_model_runner": {model}, "vllm": set()}

    monkeypatch.setattr(
        catalog_probes,
        "installed_runtime_models",
        fake_installed,
    )

    entries, default = await list_catalog_with_availability()
    repody_vlm_entry = next(e for e in entries if e.spec.id == REPODY_VLM_CATALOG_ID)
    assert repody_vlm_entry.available is True
    assert default == REPODY_VLM_CATALOG_ID


@pytest.mark.asyncio
async def test_list_catalog_skips_remote_probe(monkeypatch):
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "vllm")
    monkeypatch.setenv(
        "AUDIT_VLLM_BASE_URL",
        "https://gpu.example.com/v1",
    )
    monkeypatch.setenv("AUDIT_GPU_LIVE_PROBE", "false")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()

    async def fail_if_called(*args, **kwargs):
        raise AssertionError(
            "installed_runtime_models should not call remote vLLM when probe disabled"
        )

    from audit_workbench.catalog import probes as catalog_probes

    monkeypatch.setattr(
        catalog_probes,
        "list_openai_models",
        fail_if_called,
    )

    entries, default = await list_catalog_with_availability()
    repody_vlm_entry = next(e for e in entries if e.spec.id == REPODY_VLM_CATALOG_ID)
    assert repody_vlm_entry.available is True
    assert repody_vlm_entry.availability_note is not None
    assert default == REPODY_VLM_CATALOG_ID
    get_settings.cache_clear()


def test_availability_note_for_missing_vllm_model(monkeypatch):
    monkeypatch.setenv("AUDIT_INFERENCE_MODE", "vllm")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    spec = parse_document_model(REPODY_VLM_CATALOG_ID)
    available, note = availability_for_spec(spec, installed_by_runtime={"vllm": set()})
    assert available is False
    assert note is not None
    get_settings.cache_clear()
