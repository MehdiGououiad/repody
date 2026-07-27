import json

import pytest

from audit_workbench.integration.facture import facture_bytes


@pytest.mark.live
@pytest.mark.asyncio
async def test_multipart_run_accepts_document_types(live_client):
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
                "documentModelId": "repody:vlm",
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
    res = await live_client.post("/v1/workflows/wf-invoice-audit/runs", files=form)
    assert res.status_code == 202, res.text
    run_id = res.json()["runId"]

    from audit_workbench.integration.workflow_flow import poll_run_until_done

    result = await poll_run_until_done(live_client, run_id)
    assert result is not None
    docs = result.get("documents") or []
    assert any(d.get("documentType") == "Invoice" and d.get("fileName") for d in docs)
