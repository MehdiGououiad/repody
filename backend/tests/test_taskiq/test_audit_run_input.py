from audit_workbench.taskiq.models import AuditRunInput


def test_audit_run_input_defaults():
    payload = AuditRunInput(run_id="run-1")
    assert payload.extract_pool == "extract"
    assert payload.workflow_id is None
