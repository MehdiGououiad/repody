"""Shared integration fixture paths."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_facture_pdf() -> Path:
    if env := os.environ.get("FACTURE_PDF"):
        return Path(env)
    candidates = [
        repo_root() / "e2e" / "fixtures" / "documents" / "Facture.pdf",
        Path("/app/e2e/fixtures/documents/Facture.pdf"),
    ]
    for path in candidates:
        resolved = path.resolve()
        if resolved.is_file():
            return resolved
    return candidates[0]
