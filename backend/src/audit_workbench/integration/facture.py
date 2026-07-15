"""Shared Facture.pdf E2E helpers — expected Total TTC = 6000.00."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from audit_workbench.extraction.document_modes import LOGIC_VALIDATION, ValidationMode
from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID
from audit_workbench.integration.fixtures import resolve_facture_pdf

FACTURE_PDF = resolve_facture_pdf()
EXPECTED_TOTAL = "6000.00"
EXPECTED_TVA = "1000.00"
TOTAL_FIELD = "total_amount"
TVA_FIELD = "tva"
WORKFLOW_NAME = "Facture E2E"

def _logic_compare_rule(
    *,
    rule_id: str,
    name: str,
    field: str,
    operator: str,
    value: str,
) -> dict[str, Any]:
    """Structured conditions — API rejects body-only logic rules."""
    return {
        "id": rule_id,
        "name": name,
        "kind": "logic",
        "scope": "intra",
        "body": f"{field} {operator} {value}",
        "conditions": [
            {
                "id": f"{rule_id}-c1",
                "left": {"kind": "field", "value": field},
                "operator": operator,
                "right": {"kind": "literal", "value": value},
            }
        ],
        "conditionJunction": "AND",
        "severity": "reject",
    }


LOGIC_RULE_TOTAL_OK = _logic_compare_rule(
    rule_id="logic-total-6000",
    name="Total TTC equals 6000",
    field=TOTAL_FIELD,
    operator="==",
    value="6000",
)

LOGIC_RULE_TOTAL_FAIL = _logic_compare_rule(
    rule_id="logic-total-wrong",
    name="Total must not be 1",
    field=TOTAL_FIELD,
    operator="==",
    value="1",
)

LOGIC_RULE_TVA_UNDER_500 = _logic_compare_rule(
    rule_id="logic-tva-under-500",
    name="TVA under 500",
    field=TVA_FIELD,
    operator="<",
    value="500",
)

LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS = {
    "id": "logic-tva-ui-conditions",
    "name": "TVA under 500 (UI conditions)",
    "kind": "logic",
    "scope": "intra",
    "body": "",
    "conditions": [
        {
            "id": "c1",
            "left": {"kind": "field", "value": "tva"},
            "operator": "<",
            "right": {"kind": "literal", "value": "500"},
        }
    ],
    "conditionJunction": "AND",
    "severity": "reject",
}


@dataclass(frozen=True)
class FacturePathCase:
    id: str
    read_path: str
    validation_mode: ValidationMode
    document_model_id: str = REPODY_VLM_CATALOG_ID
    max_wait_ms: float = 900_000


FACTURE_UI_PATHS: tuple[FacturePathCase, ...] = (
    FacturePathCase(
        id="document_model_logic",
        read_path="document_model",
        validation_mode="logic_only",
    ),
)


def facture_bytes() -> bytes:
    if not FACTURE_PDF.is_file():
        raise FileNotFoundError(f"Missing fixture: {FACTURE_PDF}")
    return FACTURE_PDF.read_bytes()


def validation_mode_for_path(_extraction_mode: str) -> ValidationMode:
    return LOGIC_VALIDATION


def rules_for_case(case: FacturePathCase) -> list[dict]:
    return [
        {
            **LOGIC_RULE_TOTAL_OK,
            "id": f"logic-total-{uuid.uuid4().hex[:8]}",
        }
    ]


def document_def(case: FacturePathCase, *, doc_id: str) -> dict[str, Any]:
    return {
        "id": doc_id,
        "documentType": "Invoice",
        "extractionMode": case.read_path,
        "validationMode": case.validation_mode,
        "documentModelId": case.document_model_id,
        "schema": [
            {
                "id": new_field_id(),
                "name": TOTAL_FIELD,
                "description": "Total TTC",
            }
        ],
    }


def document_def_tva(case: FacturePathCase, *, doc_id: str) -> dict[str, Any]:
    doc = document_def(case, doc_id=doc_id)
    doc["schema"] = [
        {
            "id": new_field_id(),
            "name": TVA_FIELD,
            "description": "Total TVA",
        }
    ]
    return doc


def new_doc_id() -> str:
    return f"doc-{uuid.uuid4().hex[:8]}"


def new_field_id() -> str:
    return f"f-{uuid.uuid4().hex[:8]}"


def _field_value(result: dict, key: str) -> str | None:
    for doc in result.get("documents") or []:
        for field in doc.get("fields") or []:
            if field.get("key") == key or field.get("name") == key:
                value = field.get("value")
                return str(value) if value is not None else None
    return None


def total_from_result(result: dict) -> str | None:
    return _field_value(result, TOTAL_FIELD)


def tva_from_result(result: dict) -> str | None:
    return _field_value(result, TVA_FIELD)


def rule_status_from_result(result: dict, *, rule_name: str) -> str | None:
    # API may append ": <expression>" to the display name.
    for row in result.get("ruleResults") or []:
        name = str(row.get("name") or "")
        if name == rule_name or name.startswith(f"{rule_name}:"):
            return row.get("status")
    return None
