"""Normalize legacy extraction_mode and ocr_model values.

Revision ID: g1h2i3j4k5l6
Revises: e5f6a7b8c9d0
Create Date: 2026-06-30
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_EXTRACTION_MODES = frozenset({"paddle", "paddle_ocr", "ocr", "pp-ocrv6"})
REPODY_VLM_CATALOG_ID = "repody:vlm"
DOCUMENT_MODEL_READ_PATH = "document_model"


def _normalize_extraction_mode(value: str | None) -> str:
    raw = (value or DOCUMENT_MODEL_READ_PATH).strip().lower()
    if raw in LEGACY_EXTRACTION_MODES:
        return DOCUMENT_MODEL_READ_PATH
    if raw == DOCUMENT_MODEL_READ_PATH:
        return DOCUMENT_MODEL_READ_PATH
    return DOCUMENT_MODEL_READ_PATH


def _normalize_ocr_model(value: str | None) -> str:
    stripped = (value or "").strip()
    if stripped == REPODY_VLM_CATALOG_ID:
        return REPODY_VLM_CATALOG_ID
    return REPODY_VLM_CATALOG_ID


def _normalize_validation_mode(value: str | None) -> str:
    raw = (value or "logic_only").strip().lower()
    if raw == "logic_and_llm":
        return "logic_and_llm"
    return "logic_only"


def _normalize_snapshot_document(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    for mode_key in ("extractionMode", "extraction_mode"):
        if mode_key in out:
            out[mode_key] = _normalize_extraction_mode(str(out[mode_key]))
    for model_key in ("ocrModel", "ocr_model"):
        if model_key in out:
            out[model_key] = _normalize_ocr_model(
                str(out[model_key]) if out[model_key] is not None else None
            )
    for val_key in ("validationMode", "validation_mode"):
        if val_key in out:
            out[val_key] = _normalize_validation_mode(
                str(out[val_key]) if out[val_key] is not None else None
            )
    return out


def _normalize_run_snapshot(snapshot: Any) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict):
        return None
    out = dict(snapshot)
    raw_docs = out.get("documents")
    if isinstance(raw_docs, list):
        out["documents"] = [
            _normalize_snapshot_document(doc) if isinstance(doc, dict) else doc
            for doc in raw_docs
        ]
    return out


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE documents
            SET extraction_mode = :target
            WHERE lower(trim(extraction_mode)) IN ('paddle', 'paddle_ocr', 'ocr', 'pp-ocrv6')
            """
        ),
        {"target": DOCUMENT_MODEL_READ_PATH},
    )
    conn.execute(
        sa.text(
            """
            UPDATE documents
            SET ocr_model = :target
            WHERE ocr_model IS NULL
               OR trim(ocr_model) = ''
               OR trim(ocr_model) <> :target
            """
        ),
        {"target": REPODY_VLM_CATALOG_ID},
    )

    rows = conn.execute(sa.text("SELECT id, run_snapshot FROM runs WHERE run_snapshot IS NOT NULL"))
    for row in rows:
        normalized = _normalize_run_snapshot(row.run_snapshot)
        if normalized is None:
            continue
        conn.execute(
            sa.text("UPDATE runs SET run_snapshot = :snapshot WHERE id = :run_id"),
            {"snapshot": json.dumps(normalized), "run_id": row.id},
        )


def downgrade() -> None:
    pass
