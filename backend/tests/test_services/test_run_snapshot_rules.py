from audit_workbench.services.run.snapshot import resolve_run_rules


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
