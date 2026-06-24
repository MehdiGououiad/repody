from __future__ import annotations

LLM_RULE_FEW_SHOT = """
Examples:
Rule: "Verify @total_amount is positive."
Fields: total_amount=6000
-> {"passed":true,"detail":"total_amount is positive."}

Rule: "Ensure @vendor_name mentions Acme."
Fields: vendor_name=Globex Corp
-> {"passed":false,"detail":"vendor_name is Globex Corp, not Acme."}
""".strip()


def fields_block(field_values: dict[str, str]) -> str:
    lines = [
        f"{key}={value}"
        for key, value in field_values.items()
        if value and value != "\u2014"
    ]
    return "\n".join(lines[:40]) or "(no values)"


def single_rule_prompt(
    *,
    rule_name: str,
    body: str,
    field_values: dict[str, str],
) -> str:
    return (
        f"{LLM_RULE_FEW_SHOT}\n\n"
        f'Audit rule "{rule_name}": {body}\n'
        f"Fields:\n{fields_block(field_values)}\n"
        'JSON only: {"passed":true|false,"detail":"..."}'
    )


def batch_rules_block(rules: list[dict]) -> str:
    return "\n".join(
        f'- id="{rule.get("id")}": {rule.get("name")} \u2014 {(rule.get("body") or "").strip()}'
        for rule in rules
    )


def batch_rules_prompt(
    *,
    rules: list[dict],
    field_values: dict[str, str],
) -> str:
    return (
        f"{LLM_RULE_FEW_SHOT}\n\n"
        "Evaluate each audit rule against the field values.\n"
        f"Fields:\n{fields_block(field_values)}\n\n"
        f"Rules:\n{batch_rules_block(rules)}\n\n"
        "JSON only: "
        '{"results":[{"id":"<rule id>","passed":true|false,"detail":"..."}]}\n'
    )
