"""Sample documents the tests upload (shared with the Playwright e2e fixtures)."""

from pathlib import Path

FACTURE_PDF = Path(__file__).resolve().parents[2] / "e2e" / "fixtures" / "documents" / "Facture.pdf"
PDF = FACTURE_PDF.read_bytes()
# One file for a run, as the multipart form sends it.
FILE = {"files": ("facture.pdf", PDF, "application/pdf")}
