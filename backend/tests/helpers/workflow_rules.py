"""Structured logic rule payloads for workflow API tests."""


def _condition_gt(field: str, value: str, *, cid: str = "c1") -> dict:
    return {
        "id": cid,
        "left": {"kind": "field", "value": field},
        "operator": ">",
        "right": {"kind": "literal", "value": value},
    }


def logic_field_gt(
    *,
    rule_id: str,
    name: str,
    doc_id: str,
    field: str,
    value: str,
    severity: str = "reject",
) -> dict:
    body = f"{field} > {value}"
    return {
        "id": rule_id,
        "name": name,
        "kind": "logic",
        "scope": "intra",
        "appliesTo": [doc_id],
        "conditions": [_condition_gt(field, value, cid=f"{rule_id}-c1")],
        "body": body,
        "severity": severity,
    }


def logic_sum_equals(
    *,
    rule_id: str,
    name: str,
    left: str,
    extra: str,
    right: str,
    severity: str = "reject",
    scope: str = "intra",
    applies_to: list[str] | None = None,
) -> dict:
    body = f"{left} + {extra} == {right}"
    return {
        "id": rule_id,
        "name": name,
        "kind": "logic",
        "scope": scope,
        "appliesTo": applies_to or [],
        "conditions": [
            {
                "id": f"{rule_id}-c1",
                "left": {"kind": "field", "value": left},
                "arithmeticOp": "+",
                "leftExtra": {"kind": "field", "value": extra},
                "operator": "==",
                "right": {"kind": "field", "value": right},
            }
        ],
        "body": body,
        "severity": severity,
    }


def logic_field_compare(
    *,
    rule_id: str,
    name: str,
    left: str,
    operator: str,
    right: str,
    severity: str = "reject",
    scope: str = "intra",
    applies_to: list[str] | None = None,
) -> dict:
    body = f"{left} {operator} {right}"
    left_operand = {"kind": "field", "value": left}
    right_operand = (
        {"kind": "literal", "value": right}
        if operator in (">", ">=", "<", "<=", "==", "!=")
        and right.replace(".", "", 1).replace("-", "", 1).isdigit()
        else {"kind": "field", "value": right}
    )
    return {
        "id": rule_id,
        "name": name,
        "kind": "logic",
        "scope": scope,
        "appliesTo": applies_to or [],
        "conditions": [
            {
                "id": f"{rule_id}-c1",
                "left": left_operand,
                "operator": operator,
                "right": right_operand,
            }
        ],
        "body": body,
        "severity": severity,
    }
