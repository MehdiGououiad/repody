from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from audit_workbench.services.run_pool_classifier import resolve_worker_pool
from audit_workbench.settings import Settings, clear_settings_cache


@pytest.fixture
def pool_settings(monkeypatch):
    clear_settings_cache()
    return Settings()


@pytest.mark.asyncio
async def test_resolve_worker_pool_no_files_uses_fast(pool_settings):
    session = AsyncMock()
    run = MagicMock()
    run.worker_pool = None
    run.workflow_id = "wf-1"
    run.documents = [MagicMock(storage_key=None)]

    run_result = MagicMock()
    run_result.scalar_one_or_none.return_value = run
    wf_result = MagicMock()
    wf_result.scalar_one_or_none.return_value = MagicMock(documents=[])
    session.execute = AsyncMock(side_effect=[run_result, wf_result])

    pool = await resolve_worker_pool(session, "run-1")
    assert pool == "fast"


@pytest.mark.asyncio
async def test_resolve_worker_pool_uploaded_auto_uses_ocr(pool_settings):
    session = AsyncMock()
    run = MagicMock()
    run.worker_pool = None
    run.workflow_id = "wf-1"
    run_doc = MagicMock(storage_key="runs/x/file.pdf", document_id="doc-1")
    run.documents = [run_doc]

    wf = MagicMock()
    wf_doc = MagicMock(id="doc-1", extraction_mode="auto")
    wf.documents = [wf_doc]

    run_result = MagicMock()
    run_result.scalar_one_or_none.return_value = run
    wf_result = MagicMock()
    wf_result.scalar_one_or_none.return_value = wf
    session.execute = AsyncMock(side_effect=[run_result, wf_result])

    pool = await resolve_worker_pool(session, "run-2")
    assert pool == "ocr"


@pytest.mark.asyncio
async def test_resolve_worker_pool_uploaded_document_model_uses_ocr(pool_settings):
    session = AsyncMock()
    run = MagicMock()
    run.worker_pool = None
    run.workflow_id = "wf-1"
    run_doc = MagicMock(storage_key="runs/x/scan.pdf", document_id="doc-scan")
    run.documents = [run_doc]

    wf = MagicMock()
    wf.documents = [MagicMock(id="doc-scan", extraction_mode="document_model")]

    run_result = MagicMock()
    run_result.scalar_one_or_none.return_value = run
    wf_result = MagicMock()
    wf_result.scalar_one_or_none.return_value = wf
    session.execute = AsyncMock(side_effect=[run_result, wf_result])

    pool = await resolve_worker_pool(session, "run-4")
    assert pool == "ocr"
