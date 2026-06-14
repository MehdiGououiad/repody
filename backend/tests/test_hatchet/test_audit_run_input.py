from audit_workbench.hatchet.workflows.audit_run import AuditRunInput


def test_audit_run_input_carries_correlation_fields() -> None:
    payload = AuditRunInput(
        run_id="run_1",
        extract_pool="ocr",
        workflow_id="wf_1",
        request_id="req_abc",
    )
    assert payload.workflow_id == "wf_1"
    assert payload.request_id == "req_abc"
