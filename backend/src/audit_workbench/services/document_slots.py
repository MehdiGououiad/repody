from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class _WorkflowDocument(Protocol):
    id: str
    document_type: str


def _document_type(doc: _WorkflowDocument) -> str:
    return (doc.document_type or "").strip()


def resolve_document_slot_keys(
    workflow_docs: Sequence[_WorkflowDocument],
    keys: list[str],
) -> list[str]:
    """Map upload slot keys to workflow document ids.

    Each key may be an internal document id or the configured document type name
    (case-insensitive). Raises ValueError when unknown or ambiguous.
    """
    by_id = {doc.id: doc for doc in workflow_docs}
    by_type: dict[str, list[str]] = {}
    for doc in workflow_docs:
        doc_type = _document_type(doc)
        if not doc_type:
            continue
        by_type.setdefault(doc_type.casefold(), []).append(doc.id)

    resolved: list[str] = []
    for key in keys:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Each document slot must be a non-empty string.")

        if key in by_id:
            resolved.append(key)
            continue

        matches = by_type.get(key.strip().casefold(), [])
        if len(matches) == 1:
            resolved.append(matches[0])
            continue
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous document type {key!r} — multiple slots share this name; use document id."
            )
        raise ValueError(
            f"Unknown document slot {key!r} — use a configured document type name or document id."
        )

    return resolved
