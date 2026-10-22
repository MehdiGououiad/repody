from repody.app.run.snapshot import materialize_run_config, resolve_run_rules


def test_resolve_run_rules_preserves_applies_to_from_snapshot():
    run = type(
        "Run",
        (),
        {
            "run_snapshot": {
                "rules": [
                    {
                        "id": "r1",
                        "scope": "intra",
                        "appliesTo": ["doc-a"],
                        "body": "total > 1",
                    }
                ]
            },
            "workflow": None,
        },
    )()
    rules = resolve_run_rules(run, workflow=type("Workflow", (), {})())
    assert rules[0]["applies_to"] == ["doc-a"]


def test_materialize_run_config_reads_documents_and_rules_together():
    run = type(
        "Run",
        (),
        {
            "run_snapshot": {
                "workflowName": "Invoices",
                "documents": [
                    {
                        "id": "doc-a",
                        "documentType": "invoice",
                        "position": 0,
                        "schema": [{"name": "total", "templateType": "number"}],
                    }
                ],
                "rules": [
                    {
                        "id": "r1",
                        "scope": "intra",
                        "appliesTo": ["doc-a"],
                        "body": "total > 1",
                    }
                ],
            },
            "workflow": None,
        },
    )()
    config = materialize_run_config(run)
    assert config.workflow_name == "Invoices"
    assert config.documents[0].id == "doc-a"
    assert config.documents[0].schema_fields[0].name == "total"
    assert config.rules[0]["applies_to"] == ["doc-a"]
