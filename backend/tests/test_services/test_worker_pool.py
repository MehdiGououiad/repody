from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from audit_workbench.services.worker_pool import resolve_worker_pool
from audit_workbench.settings import Settings, clear_settings_cache


@pytest.fixture
def pool_settings(monkeypatch):
    clear_settings_cache()
    return Settings()


@pytest.mark.asyncio
async def test_resolve_worker_pool_no_files_uses_fast(pool_settings):
    session = AsyncMock()
    run = MagicMock()
    run.documents = [MagicMock(storage_key=None)]

    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=run)),
    )

    pool = await resolve_worker_pool(session, "run-1")
    assert pool == "fast"


@pytest.mark.asyncio
async def test_resolve_worker_pool_uploaded_auto_uses_ocr(pool_settings):
    session = AsyncMock()
    run = MagicMock()
    run.workflow_id = "wf-1"
    run_doc = MagicMock(storage_key="runs/x/file.pdf", document_id="doc-1")
    run.documents = [run_doc]

    wf = MagicMock()
    wf_doc = MagicMock(id="doc-1", extraction_mode="auto")
    wf.documents = [wf_doc]

    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=run)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=wf)),
        ]
    )

    pool = await resolve_worker_pool(session, "run-2")
    assert pool == "ocr"


@pytest.mark.asyncio
async def test_resolve_worker_pool_uploaded_document_model_uses_ocr(pool_settings):
    session = AsyncMock()
    run = MagicMock()
    run.workflow_id = "wf-1"
    run_doc = MagicMock(storage_key="runs/x/scan.pdf", document_id="doc-scan")
    run.documents = [run_doc]

    wf = MagicMock()
    wf.documents = [MagicMock(id="doc-scan", extraction_mode="document_model")]

    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=run)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=wf)),
        ]
    )

    pool = await resolve_worker_pool(session, "run-4")
    assert pool == "ocr"
