import json

import pytest

from tests.test_e2e.facture_helpers import facture_bytes


@pytest.mark.asyncio
async def test_confirm_upload_uses_object_metadata(client, monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    from audit_workbench.settings import clear_settings_cache

    clear_settings_cache()
    from audit_workbench.storage.factory import get_storage

    storage = get_storage()
    await storage.ensure_bucket()
    key = "runs/demo/doc.pdf"
    payload = b"%PDF-1.4\nsample"
    await storage.put_bytes(key, payload, "application/pdf")

    res = await client.post("/v1/uploads/confirm", json={"storageKeys": [key]})

    assert res.status_code == 200
    body = res.json()
    assert body["uploads"][0]["storageKey"] == key
    assert body["uploads"][0]["size"] == len(payload)


@pytest.mark.asyncio
async def test_duplicate_file_upload_run_completes(client, mock_ollama_llm):
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
                "ocrModel": "repody:vlm",
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
        res = await client.post("/v1/workflows/wf-invoice-audit/runs?mode=test", files=form)
        assert res.status_code == 202, res.text
        return res.json()["runId"]

    run_id_1 = await start_run()
    run_id_2 = await start_run()
    assert run_id_1 != run_id_2

    for run_id in (run_id_1, run_id_2):
        detail = await client.get(f"/v1/runs/{run_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["status"] in ("done", "failed"), body
