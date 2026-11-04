"""Generate Facture.pdf fixture matching E2E expectations (Total TTC 6000, TVA 1000).

A scanned-style invoice: the text is drawn on an A4 page image (150 DPI) saved as a PDF.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]  # backend/
OUT = ROOT.parent / "e2e" / "fixtures" / "documents" / "Facture.pdf"
DPI = 150

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
    page = Image.new("RGB", (int(8.27 * DPI), int(11.69 * DPI)), "white")
    font = ImageFont.load_default(size=int(11 * DPI / 72))
    ImageDraw.Draw(page).multiline_text((DPI, DPI), TEXT, fill="black", font=font, spacing=12)
    page.save(OUT, "PDF", resolution=DPI)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
