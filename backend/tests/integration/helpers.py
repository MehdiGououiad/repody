"""Builders for workflow payloads (camelCase, as the frontend sends them)."""

from typing import Any


def condition(left: str, op: str, right: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"id": "c1", "left": {"kind": "field", "field": left}, "operator": op}
    if right is not None:
        body["right"] = {"kind": "literal", "value": right}
    return body


def rule(rule_id: str, *conditions: dict[str, Any], severity: str = "reject") -> dict[str, Any]:
    return {"id": rule_id, "name": rule_id, "severity": severity, "conditions": list(conditions)}


def invoice_workflow(*rules: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "Invoices",
        "documents": [
            {
                "id": "doc-inv",
                "documentType": "Invoice",
                "schema": [
                    {"id": "f1", "name": "total_amount", "templateType": "number"},
                    {"id": "f2", "name": "tva", "templateType": "number"},
                ],
            }
        ],
        "rules": list(rules),
    }


def document(doc_id: str, document_type: str) -> dict[str, Any]:
    """A workflow document with one number field, ``total_amount``."""
    return {
        "id": doc_id,
        "documentType": document_type,
        "schema": [{"id": f"{doc_id}-f1", "name": "total_amount", "templateType": "number"}],
    }
