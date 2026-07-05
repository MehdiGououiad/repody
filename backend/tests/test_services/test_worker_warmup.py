from __future__ import annotations

import pytest
import structlog.testing

from audit_workbench.taskiq import worker


@pytest.mark.asyncio
async def test_extract_worker_warms_repody_vlm(monkeypatch):
    calls: list[str] = []

    async def record_vlm() -> str:
        calls.append("repody_vlm")
        return "ok"

    monkeypatch.setattr(
        worker,
        "settings",
        type("S", (), {"repody_vlm_warmup_on_start": True})(),
    )

    import audit_workbench.extraction.repody_vlm as repody_vlm_mod

    monkeypatch.setattr(repody_vlm_mod, "warmup_repody_vlm", record_vlm)

    with structlog.testing.capture_logs() as captured:
        await worker._warmup_document_models("extract")

    assert calls == ["repody_vlm"]
    summary = next(e for e in captured if e.get("event") == "extract_pool_warmup_done")
    assert summary["repody_vlm"] == "ok"


@pytest.mark.asyncio
async def test_fast_pool_skips_extract_warmup(monkeypatch):
    monkeypatch.setattr(
        "audit_workbench.taskiq.worker.get_settings",
        lambda: type("S", (), {"repody_vlm_warmup_on_start": True})(),
    )

    with structlog.testing.capture_logs() as captured:
        await worker._warmup_document_models("fast")

    assert not any(entry.get("event") == "extract_pool_warmup_done" for entry in captured)
