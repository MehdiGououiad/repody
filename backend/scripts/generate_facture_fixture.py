"""Generate Facture.pdf fixture matching E2E expectations (Total TTC 6000, TVA 1000)."""

from __future__ import annotations

from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]  # backend/
OUT = ROOT.parent / "e2e" / "fixtures" / "documents" / "Facture.pdf"

TEXT = """FACTURE N° FAC-2024-001
Date: 15/01/2024

Prestation de services

Total HT: 5000.00
Total TVA: 1000.00
Total TTC: 6000.00

Merci pour votre confiance.
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), TEXT, fontsize=11)
    doc.save(OUT)
    doc.close()
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
