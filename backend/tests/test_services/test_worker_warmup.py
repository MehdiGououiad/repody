from types import SimpleNamespace

import pytest

from audit_workbench.hatchet import worker


@pytest.mark.asyncio
async def test_ocr_worker_warms_repody_vlm(monkeypatch):
    calls: list[str] = []

    async def record() -> None:
        calls.append("repody_vlm")

    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(
            repody_vlm_warmup_on_start=True,
        ),
    )

    import audit_workbench.extraction.repody_vlm as repody_vlm_mod

    monkeypatch.setattr(repody_vlm_mod, "warmup_repody_vlm", record)

    await worker._warmup_ocr_models("ocr")

    assert calls == ["repody_vlm"]
