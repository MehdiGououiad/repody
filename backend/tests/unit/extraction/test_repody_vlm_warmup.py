from unittest.mock import AsyncMock

import pytest

from repody.extraction import warmup
from repody.settings import clear_settings_cache


@pytest.mark.asyncio
async def test_warmup_skips_when_the_document_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_REPODY_VLM_WARMUP_DOCUMENT", str(tmp_path / "missing.pdf"))
    clear_settings_cache()
    assert await warmup.warmup_repody_vlm() == "skipped"


@pytest.mark.asyncio
async def test_warmup_sends_one_request_with_the_synthetic_page(monkeypatch):
    monkeypatch.delenv("AUDIT_REPODY_VLM_WARMUP_DOCUMENT", raising=False)
    clear_settings_cache()
    post = AsyncMock(return_value={})
    monkeypatch.setattr(warmup, "post_chat_completion", post)
    assert await warmup.warmup_repody_vlm() == "ok"
    payload = post.await_args.args[1]
    assert payload["messages"][-1]["content"][0]["type"] == "image_url"


@pytest.mark.asyncio
async def test_warmup_reports_failure(monkeypatch):
    monkeypatch.delenv("AUDIT_REPODY_VLM_WARMUP_DOCUMENT", raising=False)
    clear_settings_cache()
    monkeypatch.setattr(warmup, "post_chat_completion", AsyncMock(side_effect=RuntimeError("down")))
    assert await warmup.warmup_repody_vlm() == "failed"
