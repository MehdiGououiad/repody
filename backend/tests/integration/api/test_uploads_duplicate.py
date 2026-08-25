import json

import pytest
from tests.helpers.api_errors import assert_error_response

from repody.integration.facture import facture_bytes


@pytest.mark.asyncio
async def test_confirm_upload_accepts_real_gououiad_cnie_png_named_jpeg(
    client, monkeypatch, tmp_path
):
    """Full fixture: gououiad-cnie-front.png is JPEG magic with a .png name."""
    from pathlib import Path

    monkeypatch.setenv("AUDIT_LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    from repody.settings import clear_settings_cache

    clear_settings_cache()
    from repody.app.uploads.intents import record_upload_intent
    from repody.infra.db.base import async_session_factory
    from repody.infra.storage.factory import get_storage

    fixture = (
        Path(__file__).resolve().parents[4]
        / "e2e"
        / "fixtures"
        / "documents"
        / "gououiad-cnie-front.png"
    )
    data = fixture.read_bytes()
    storage = get_storage()
    await storage.ensure_bucket()
    key = "runs/demo/gououiad-cnie-front.png"
    await storage.put_bytes(key, data, "image/png")
    async with async_session_factory() as session:
        await record_upload_intent(
            session,
            storage_key=key,
            file_name="gououiad-cnie-front.png",
            mime_type="image/png",
            size=len(data),
            owner_subject="dev-local",
        )
        await session.commit()

    res = await client.post("/v1/uploads/confirm", json={"storageKeys": [key]})
    assert res.status_code == 200, res.text
    assert res.json()["uploads"][0]["mimeType"] == "image/jpeg"


@pytest.mark.asyncio
async def test_confirm_upload_uses_object_metadata(client, monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    from repody.settings import clear_settings_cache

    clear_settings_cache()
    from repody.app.uploads.intents import record_upload_intent
    from repody.infra.db.base import async_session_factory
    from repody.infra.storage.factory import get_storage

    storage = get_storage()
    await storage.ensure_bucket()
    key = "runs/demo/doc.pdf"
    payload = b"%PDF-1.4\nsample"
    await storage.put_bytes(key, payload, "application/pdf")
    async with async_session_factory() as session:
        await record_upload_intent(
            session,
            storage_key=key,
            file_name="doc.pdf",
            mime_type="application/pdf",
            size=len(payload),
            owner_subject="dev-local",
        )
        await session.commit()

    res = await client.post("/v1/uploads/confirm", json={"storageKeys": [key]})

    assert res.status_code == 200
    body = res.json()
    assert body["uploads"][0]["storageKey"] == key
    assert body["uploads"][0]["size"] == len(payload)


@pytest.mark.asyncio
async def test_confirm_upload_rejects_unprepared_storage_key(client, monkeypatch, tmp_path):
    """VALIDATION AppError → 422 (not legacy bare 400)."""
    monkeypatch.setenv("AUDIT_LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    from repody.infra.storage.factory import get_storage
    from repody.settings import clear_settings_cache

    clear_settings_cache()
    storage = get_storage()
    await storage.ensure_bucket()
    key = "runs/unprepared/doc.pdf"
    await storage.put_bytes(key, b"%PDF-1.4\nsample", "application/pdf")

    res = await client.post("/v1/uploads/confirm", json={"storageKeys": [key]})

    assert_error_response(res, status_code=422, detail_contains="not prepared")


@pytest.mark.asyncio
async def test_run_json_rejects_unconfirmed_file_binding(client):
    """Unconfirmed bindings fail closed with VALIDATION → 422."""
    res = await client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        json={
            "snapshot": {"documents": [], "rules": []},
            "fileBindings": [
                {
                    "storageKey": "runs/unconfirmed/doc.pdf",
                    "mimeType": "application/pdf",
                    "fileName": "doc.pdf",
                }
            ],
        },
    )

    assert_error_response(res, status_code=422, detail_contains="not confirmed")


@pytest.mark.asyncio
async def test_confirm_upload_rejects_different_owner(client, monkeypatch, tmp_path):
    """FORBIDDEN AppError → 403 when intent owner ≠ principal."""
    monkeypatch.setenv("AUDIT_LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    from repody.settings import clear_settings_cache

    clear_settings_cache()
    from repody.app.uploads.intents import record_upload_intent
    from repody.infra.db.base import async_session_factory
    from repody.infra.storage.factory import get_storage

    storage = get_storage()
    await storage.ensure_bucket()
    key = "runs/demo/other-owner.pdf"
    payload = b"%PDF-1.4\nsample"
    await storage.put_bytes(key, payload, "application/pdf")
    async with async_session_factory() as session:
        await record_upload_intent(
            session,
            storage_key=key,
            file_name="other-owner.pdf",
            mime_type="application/pdf",
            size=len(payload),
            owner_subject="someone-else",
        )
        await session.commit()

    res = await client.post("/v1/uploads/confirm", json={"storageKeys": [key]})

    assert_error_response(res, status_code=403, detail_contains="different authenticated user")


@pytest.mark.live
@pytest.mark.asyncio
async def test_duplicate_file_upload_run_completes(live_client):
    """Re-running with the same bytes must not hang or error."""
    doc_id = "doc-invoice"
    try:
        pdf = facture_bytes()
    except FileNotFoundError:
        pytest.skip("Facture.pdf fixture missing")
    payload = {
        "documents": [
            {
                "id": doc_id,
                "documentType": "Invoice",
                "schema": [{"id": "f-total", "name": "total_amount", "description": "Total"}],
                "extractionMode": "document_model",
                "validationMode": "logic_only",
                "documentModelId": "repody:vlm",
            }
        ],
        "rules": [
            {
                "id": "r-total",
                "name": "Total present",
                "kind": "logic",
                "scope": "intra",
                "body": "total_amount > 0",
                "severity": "flag",
                "appliesTo": [doc_id],
            }
        ],
        "workflowName": "Duplicate upload test",
    }

    async def start_run() -> str:
        form = {
            "payload": (None, json.dumps(payload)),
            "document_ids": (None, json.dumps([doc_id])),
            "files": ("doc.pdf", pdf, "application/pdf"),
        }
        res = await live_client.post("/v1/workflows/wf-invoice-audit/runs", files=form)
        assert res.status_code == 202, res.text
        return res.json()["runId"]

    from repody.integration.workflow_flow import poll_run_until_done

    run_id_1 = await start_run()
    run_id_2 = await start_run()
    assert run_id_1 != run_id_2

    for run_id in (run_id_1, run_id_2):
        result = await poll_run_until_done(live_client, run_id)
        assert result is not None
