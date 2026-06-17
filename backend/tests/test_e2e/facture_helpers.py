"""Shared Facture.pdf E2E helpers — expected Total TTC = 6000.00."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from audit_workbench.extraction.document_modes import LOGIC_VALIDATION, ValidationMode
from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID


def _resolve_facture_pdf() -> Path:
    if env := os.environ.get("FACTURE_PDF"):
        return Path(env)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "e2e" / "fixtures" / "documents" / "Facture.pdf",
        here.parents[2].parent / "e2e" / "fixtures" / "documents" / "Facture.pdf",
        Path("/app/e2e/fixtures/documents/Facture.pdf"),
    ]
    for path in candidates:
        resolved = path.resolve()
        if resolved.is_file():
            return resolved
    return candidates[0]


FACTURE_PDF = _resolve_facture_pdf()
EXPECTED_TOTAL = "6000.00"
EXPECTED_TVA = "1000.00"
TOTAL_FIELD = "total_amount"
TVA_FIELD = "tva"
WORKFLOW_NAME = "Facture E2E"

LOGIC_RULE_TOTAL_OK = {
    "id": "logic-total-6000",
    "name": "Total TTC equals 6000",
    "kind": "logic",
    "scope": "intra",
    "body": "total_amount == 6000",
    "severity": "reject",
}

LOGIC_RULE_TOTAL_FAIL = {
    "id": "logic-total-wrong",
    "name": "Total must not be 1",
    "kind": "logic",
    "scope": "intra",
    "body": "total_amount == 1",
    "severity": "reject",
}

LOGIC_RULE_TVA_UNDER_500 = {
    "id": "logic-tva-under-500",
    "name": "TVA under 500",
    "kind": "logic",
    "scope": "intra",
    "body": "tva < 500",
    "severity": "reject",
}

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
    ocr_model: str = REPODY_VLM_CATALOG_ID
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
        "ocrModel": case.ocr_model,
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
    for row in result.get("ruleResults") or []:
        if row.get("name") == rule_name:
            return row.get("status")
    return None
