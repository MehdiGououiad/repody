import json

import pytest

from tests.test_e2e.facture_helpers import facture_bytes


@pytest.mark.asyncio
async def test_multipart_run_accepts_document_types(client, mock_ollama_llm):
    try:
        pdf = facture_bytes()
    except FileNotFoundError:
        pytest.skip("Facture.pdf fixture missing")

    payload = {
        "documents": [
            {
                "id": "doc-invoice",
                "documentType": "Invoice",
                "schema": [{"id": "f-total", "name": "total_amount", "description": "Total"}],
                "extractionMode": "document_model",
                "validationMode": "logic_only",
                "ocrModel": "repody:vlm",
            }
        ],
        "rules": [],
        "workflowName": "Document types binding test",
    }

    form = {
        "payload": (None, json.dumps(payload)),
        "document_types": (None, json.dumps(["Invoice"])),
        "files": ("doc.pdf", pdf, "application/pdf"),
    }
    res = await client.post("/v1/workflows/wf-invoice-audit/runs?mode=test", files=form)
    assert res.status_code == 202, res.text
    run_id = res.json()["runId"]

    detail = await client.get(f"/v1/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] in ("done", "failed"), body
    if body["status"] == "done":
        result = body["result"]
        assert result is not None
        docs = result.get("documents") or []
        assert any(d.get("documentType") == "Invoice" and d.get("fileName") for d in docs)
