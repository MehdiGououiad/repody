# /// script
# requires-python = ">=3.12"
# dependencies = ["reportlab>=4.4", "pillow>=13.0", "pypdfium2>=5.14", "numpy>=2.3"]
# ///
"""Benchmark pages with known content: business documents like the ones Repody audits.

    uv run make_docs.py

Writes docs/<page>.pdf and gold/<page>.json. Each gold file lists:
  values  strings that must come out exactly (amounts, numbers, dates, IBANs, ids)
  lines   running text lines (headings, addresses, paragraphs)
  tables  each table as rows of cells
Every document exists as a clean digital PDF and as a scan (rasterised, tilted, noisy, JPEG);
a few also as a low-resolution scan. Everything is seeded, so the set is the same on every run.
"""

from __future__ import annotations

import io
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
DOCS, GOLD = HERE / "docs", HERE / "gold"
W, H = A4


@dataclass
class Page:
    """Drawing helper that records what it draws as gold."""

    canvas: Canvas
    values: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    y: float = H - 25 * mm

    def text(self, s: str, *, size: float = 10, bold: bool = False, x: float = 20 * mm, gap: float = 5.2) -> None:
        self.canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.canvas.drawString(x, self.y, s)
        self.lines.append(s)
        self.y -= gap * mm * size / 10

    def pair(self, label: str, value: str, *, x: float = 20 * mm, size: float = 10) -> None:
        """`label value` on one line; the value is scored exactly."""
        self.canvas.setFont("Helvetica", size)
        self.canvas.drawString(x, self.y, f"{label} {value}")
        self.lines.append(f"{label} {value}")
        self.values.append(value)
        self.y -= 5.2 * mm * size / 10

    def table(
        self,
        header: list[str],
        rows: list[list[str]],
        widths: list[float],
        *,
        values_from: int = 1,
        size: float = 9,
        ruled: bool = True,
    ) -> None:
        """A table (ruled or not); cells from column `values_from` on are scored exactly."""
        c, x0, row_h = self.canvas, 20 * mm, 7 * mm * size / 9
        xs = [x0]
        for w in widths:
            xs.append(xs[-1] + w * mm)
        top = self.y + 4.5 * mm
        for i, row in enumerate([header, *rows]):
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", size)
            for j, cell in enumerate(row):
                if j == 0:
                    c.drawString(xs[j] + 1.5 * mm, self.y, cell)
                else:
                    c.drawRightString(xs[j + 1] - 1.5 * mm, self.y, cell)
            self.y -= row_h
        bottom = self.y + 4.5 * mm
        if ruled:
            for k in range(len(rows) + 2):
                yy = top - k * row_h
                c.line(xs[0], yy, xs[-1], yy)
            for xx in xs:
                c.line(xx, top, xx, bottom)
        self.tables.append([header, *rows])
        for row in rows:
            self.values += [cell for cell in row[values_from:] if cell]
        self.y -= 4 * mm


def eur(v: float, lang: str) -> str:
    """French `1 234,50 €`, English `€1,234.50`."""
    if lang != "fr":
        return f"€{v:,.2f}"
    whole, cents = f"{v:,.2f}".split(".")
    return f"{whole.replace(',', ' ')},{cents} €"


def invoice(p: Page, rng: random.Random, lang: str) -> None:
    fr = lang == "fr"
    vendor = rng.choice(["Atelier Moreau SARL", "Boulangerie Lefèvre", "Cabinet Dubois & Associés"]) if fr else rng.choice(["Northwind Supplies Ltd", "Harbor Logistics Inc."])
    number = f"{'FAC' if fr else 'INV'}-2026-{rng.randint(1000, 9999)}"
    p.text(vendor, size=16, bold=True, gap=7)
    p.text("12 rue des Lilas, 69003 Lyon" if fr else "48 King Street, Manchester M2 4LQ")
    p.pair("SIRET :" if fr else "VAT No:", f"{rng.randint(100, 999)} {rng.randint(100, 999)} {rng.randint(100, 999)} 000{rng.randint(10, 99)}" if fr else f"GB{rng.randint(100000000, 999999999)}")
    p.y -= 4 * mm
    p.text("FACTURE" if fr else "INVOICE", size=14, bold=True, gap=7)
    p.pair("Facture n° :" if fr else "Invoice number:", number)
    p.pair("Date :" if fr else "Date:", f"{rng.randint(10, 28)}/0{rng.randint(1, 9)}/2026")
    p.pair("Échéance :" if fr else "Due date:", f"{rng.randint(10, 28)}/1{rng.randint(0, 2)}/2026")
    p.text("Client : Société Générale de Transport, 5 avenue Foch, 75116 Paris" if fr else "Bill to: Acme Retail Group, 300 Market St, Leeds LS1 6AB")
    p.y -= 3 * mm
    items = rng.sample(
        ["Maintenance annuelle", "Installation réseau", "Licence logicielle", "Formation (2 jours)", "Audit de sécurité", "Déplacement"]
        if fr else ["Annual maintenance", "Network installation", "Software licence", "Training (2 days)", "Security audit", "Travel"],
        5,
    )
    rows, subtotal = [], 0.0
    for item in items:
        qty, unit = rng.randint(1, 12), rng.randint(40, 1500) + rng.choice([0, 0.5, 0.25, 0.9])
        total = round(qty * unit, 2)
        subtotal += total
        rows.append([item, str(qty), eur(unit, lang), eur(total, lang)])
    p.table(["Désignation", "Qté", "Prix unitaire HT", "Total HT"] if fr else ["Description", "Qty", "Unit price", "Amount"], rows, [70, 18, 40, 40])
    tax = round(subtotal * 0.2, 2)
    p.pair("Total HT :" if fr else "Subtotal:", eur(subtotal, lang), x=110 * mm)
    p.pair("TVA 20 % :" if fr else "VAT 20%:", eur(tax, lang), x=110 * mm)
    p.pair("Total TTC :" if fr else "Total due:", eur(subtotal + tax, lang), x=110 * mm)
    p.y -= 6 * mm
    p.pair("IBAN :" if fr else "IBAN:", f"FR76 3000 {rng.randint(1000, 9999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)} 123" if fr else f"GB29 NWBK 6016 1331 {rng.randint(1000, 9999)} {rng.randint(10, 99)}")
    p.text("Pénalités de retard : trois fois le taux d'intérêt légal." if fr else "Payment terms: 30 days net. Late payments incur interest at 8% above base rate.")


def purchase_order(p: Page, rng: random.Random) -> None:
    p.text("BON DE COMMANDE", size=15, bold=True, gap=7)
    p.pair("N° de commande :", f"BC-{rng.randint(10000, 99999)}")
    p.pair("Date de commande :", f"0{rng.randint(1, 9)}/0{rng.randint(1, 9)}/2026")
    p.text("Fournisseur : Métallerie Rousseau, ZI des Forges, 42000 Saint-Étienne")
    p.text("Livraison : Entrepôt Nord, 18 chemin du Port, 59140 Dunkerque")
    p.y -= 3 * mm
    rows, total = [], 0.0
    for ref, label in rng.sample([("TL-204", "Tôle acier 2 mm"), ("VR-118", "Vis inox M8"), ("PR-330", "Profilé alu 40x40"), ("CH-907", "Charnière renforcée"), ("JT-055", "Joint caoutchouc")], 4):
        qty, unit = rng.randint(5, 400), rng.randint(2, 90) + 0.5
        total += qty * unit
        rows.append([f"{ref} {label}", str(qty), eur(unit, "fr"), eur(qty * unit, "fr")])
    p.table(["Article", "Quantité", "Prix unitaire", "Montant"], rows, [75, 22, 35, 36])
    p.pair("Montant total HT :", eur(total, "fr"), x=105 * mm)
    p.text("Conditions : paiement à 45 jours fin de mois.")


def bank_statement(p: Page, rng: random.Random) -> None:
    p.text("RELEVÉ DE COMPTE", size=15, bold=True, gap=7)
    p.text("Banque Populaire du Rhône — Agence Bellecour")
    p.pair("Compte n° :", f"{rng.randint(10000, 99999)} {rng.randint(10000, 99999)} {rng.randint(10000000000, 99999999999)} {rng.randint(10, 99)}")
    p.pair("Période :", "du 01/10/2026 au 31/10/2026")
    p.y -= 3 * mm
    balance = rng.randint(2000, 9000) + 0.37
    p.pair("Solde initial :", eur(balance, "fr"))
    rows = []
    labels = ["CB CARREFOUR LYON", "VIR SALAIRE OCTOBRE", "PRLV EDF", "CB SNCF CONNECT", "CHQ 0004521", "VIR LOYER", "CB AMAZON EU", "PRLV FREE MOBILE", "CB PHARMACIE CENTRALE", "VIR REMBOURSEMENT", "FRAIS TENUE DE COMPTE", "CB DECATHLON"]
    for day, label in enumerate(rng.sample(labels, 10), start=2):
        amount = rng.randint(5, 900) + rng.choice([0.1, 0.45, 0.99, 0.0])
        credit = label.startswith("VIR SALAIRE") or label.startswith("VIR REMB")
        balance += amount if credit else -amount
        rows.append([f"{day:02d}/10 {label}", "" if credit else eur(amount, "fr"), eur(amount, "fr") if credit else ""])
    p.table(["Date / Libellé", "Débit", "Crédit"], rows, [100, 34, 34])
    p.pair("Nouveau solde :", eur(balance, "fr"))


def receipt(p: Page, rng: random.Random) -> None:
    p.text("SUPERMARCHÉ DU CENTRE", size=13, bold=True, x=60 * mm, gap=6)
    p.text("8 place de la République, 33000 Bordeaux", x=60 * mm)
    p.pair("Ticket", f"n° {rng.randint(100000, 999999)}", x=60 * mm)
    p.y -= 2 * mm
    total = 0.0
    for name in rng.sample(["LAIT DEMI-ECREME 1L", "PAIN DE CAMPAGNE", "POMMES GALA 1KG", "CAFE MOULU 250G", "YAOURT NATURE X8", "HUILE D'OLIVE 75CL", "RIZ BASMATI 1KG"], 6):
        price = rng.randint(1, 9) + rng.choice([0.15, 0.49, 0.89, 0.05])
        total += price
        p.canvas.setFont("Courier", 10)
        p.canvas.drawString(60 * mm, p.y, name)
        p.canvas.drawRightString(150 * mm, p.y, f"{price:.2f}".replace(".", ","))
        p.lines.append(name)
        p.values.append(f"{price:.2f}".replace(".", ","))
        p.y -= 5 * mm
    p.y -= 2 * mm
    p.pair("TOTAL EUR", f"{total:.2f}".replace(".", ","), x=60 * mm, size=12)
    p.text("Merci de votre visite - A bientôt", x=60 * mm)


def form(p: Page, rng: random.Random) -> None:
    p.text("DEMANDE D'OUVERTURE DE COMPTE PROFESSIONNEL", size=13, bold=True, gap=8)
    for label, value in [
        ("Raison sociale :", "Transports Garnier & Fils"),
        ("Forme juridique :", "SAS"),
        ("SIREN :", f"{rng.randint(100, 999)} {rng.randint(100, 999)} {rng.randint(100, 999)}"),
        ("Code NAF :", "4941A"),
        ("Date de création :", f"1{rng.randint(0, 9)}/0{rng.randint(1, 9)}/2019"),
        ("Capital social :", eur(rng.randint(10, 500) * 1000, "fr")),
        ("Dirigeant :", "Mme Claire Garnier"),
        ("Téléphone :", f"04 7{rng.randint(1, 9)} {rng.randint(10, 99)} {rng.randint(10, 99)} {rng.randint(10, 99)}"),
        ("Courriel :", "contact@garnier-transports.fr"),
        ("Chiffre d'affaires 2025 :", eur(rng.randint(200, 9000) * 1000 + 450, "fr")),
    ]:
        p.pair(label, value)
        p.y -= 2 * mm
    p.text("Fait à Grenoble, le 22/09/2026")
    p.text("Signature précédée de la mention « lu et approuvé »")


def long_invoice(p: Page, rng: random.Random) -> None:
    """A dense invoice: 22 lines in 7.5 pt, references in the description column."""
    p.text("Distribution Électrique du Sud-Ouest", size=13, bold=True, gap=6)
    p.text("Zone Artisanale des Pins, 31700 Blagnac - Tél. 05 61 30 22 18")
    p.text("FACTURE", size=12, bold=True, gap=6)
    p.pair("Facture n° :", f"DES-{rng.randint(100000, 999999)}")
    p.pair("Date :", "03/11/2026")
    rows, subtotal = [], 0.0
    parts = ["Câble R2V 3G2,5", "Disjoncteur 16A", "Gaine ICTA 20mm", "Boîte de dérivation", "Interrupteur va-et-vient",
             "Prise 2P+T", "Tableau 3 rangées", "Différentiel 40A 30mA", "Spot LED encastré", "Domino 12 bornes", "Goulotte 40x25"]
    for k in range(22):
        ref = f"{rng.choice('ABCDEFGH')}{rng.randint(1000, 9999)}"
        qty, unit = rng.randint(1, 60), rng.randint(1, 240) + rng.choice([0.15, 0.5, 0.99, 0.0])
        total = round(qty * unit, 2)
        subtotal += total
        rows.append([f"{ref} {parts[k % len(parts)]}", str(qty), eur(unit, "fr"), eur(total, "fr")])
    p.table(["Réf. / Désignation", "Qté", "PU HT", "Montant HT"], rows, [78, 16, 34, 40], size=7.5)
    tax = round(subtotal * 0.2, 2)
    p.pair("Total HT :", eur(subtotal, "fr"), x=110 * mm, size=9)
    p.pair("TVA 20 % :", eur(tax, "fr"), x=110 * mm, size=9)
    p.pair("Net à payer :", eur(subtotal + tax, "fr"), x=110 * mm, size=9)


def dense_statement(p: Page, rng: random.Random) -> None:
    """A bank statement of 30 operations in 7 pt with no ruling lines."""
    p.text("CRÉDIT MUTUEL DE BRETAGNE - Relevé n° 11", size=12, bold=True, gap=6)
    p.pair("IBAN :", f"FR76 1558 9{rng.randint(100, 999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)} {rng.randint(100, 999)}", size=9)
    labels = ["CB LECLERC BREST", "PRLV URSSAF", "VIR CLIENT DUPONT", "CB TOTAL ENERGIES", "PRLV ORANGE PRO", "VIR FOURNISSEUR ALBA",
              "CB METRO QUIMPER", "COMMISSION CB", "VIR CLIENT KERGOAT", "PRLV ASSURANCE AXA"]
    rows = []
    for day in range(30):
        label = rng.choice(labels)
        amount = rng.randint(3, 2500) + rng.choice([0.2, 0.47, 0.99, 0.0])
        credit = label.startswith("VIR CLIENT")
        rows.append([f"{day % 28 + 1:02d}/10 {label}", "" if credit else eur(amount, "fr"), eur(amount, "fr") if credit else ""])
    p.table(["Opération", "Débit", "Crédit"], rows, [100, 34, 34], size=7, ruled=False)


CONTRACT = [
    ("Article 1 - Objet", "Le présent contrat a pour objet de définir les conditions dans lesquelles le Prestataire assure la maintenance des équipements informatiques du Client."),
    ("Article 2 - Durée", "Le contrat est conclu pour une durée de trente-six (36) mois à compter du 1er janvier 2027. Il se renouvelle par tacite reconduction pour des périodes de douze mois."),
    ("Article 3 - Prix", "En contrepartie des prestations, le Client verse une redevance annuelle de 18 450,00 € HT, payable par trimestre à terme échu, soit 4 612,50 € HT par trimestre."),
    ("Article 4 - Résiliation", "Chaque partie peut résilier le contrat par lettre recommandée avec accusé de réception, moyennant un préavis de trois mois avant l'échéance annuelle."),
    ("Article 5 - Responsabilité", "La responsabilité du Prestataire est limitée aux dommages directs et ne peut excéder le montant des sommes versées au cours des douze derniers mois."),
]


def contract(p: Page, _rng: random.Random) -> None:
    p.text("CONTRAT DE PRESTATION DE SERVICES", size=14, bold=True, gap=8)
    p.text("Entre la société Infogérance Alpine SAS, ci-après « le Prestataire »,")
    p.text("et la société Clinique Saint-Joseph, ci-après « le Client ».")
    p.y -= 3 * mm
    for heading, body in CONTRACT:
        p.text(heading, bold=True, size=11)
        words, line = body.split(), ""
        for word in words:
            if len(line) + len(word) > 92:
                p.text(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        p.text(line)
        p.y -= 2 * mm
    p.values += ["18 450,00 €", "4 612,50 €", "1er janvier 2027"]


DOCUMENTS = {
    "fr_invoice": lambda p, r: invoice(p, r, "fr"),
    "en_invoice": lambda p, r: invoice(p, r, "en"),
    "fr_purchase_order": purchase_order,
    "fr_bank_statement": bank_statement,
    "fr_receipt": receipt,
    "fr_form": form,
    "fr_contract": contract,
    "fr_long_invoice": long_invoice,
    "fr_dense_statement": dense_statement,
}
SCANNED = list(DOCUMENTS)
LOW_RES = ["fr_invoice", "fr_bank_statement", "fr_receipt"]
PHOTO = ["fr_invoice", "en_invoice", "fr_receipt", "fr_form", "fr_long_invoice"]
FAX = ["fr_purchase_order", "fr_contract", "fr_dense_statement"]


def scan(pdf: bytes, rng: random.Random, dpi: int) -> bytes:
    """A photocopy: rasterised at `dpi`, tilted, grey noise, blur, JPEG, wrapped back in a PDF."""
    with pdfium.PdfDocument(pdf) as doc:
        image = doc[0].render(scale=dpi / 72).to_pil().convert("L")
    image = image.rotate(rng.uniform(-1.8, 1.8), resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255)
    noise = np.random.default_rng(rng.randint(0, 2**31)).normal(0, 14, (image.height, image.width))
    image = Image.fromarray(np.clip(np.asarray(image, dtype=np.float32) * 0.93 + 10 + noise, 0, 255).astype("uint8"))
    image = image.filter(ImageFilter.GaussianBlur(0.6))
    jpeg = io.BytesIO()
    image.save(jpeg, "JPEG", quality=55)
    out = io.BytesIO()
    Image.open(jpeg).save(out, "PDF", resolution=dpi)
    return out.getvalue()


def render(pdf: bytes, dpi: int) -> Image.Image:
    with pdfium.PdfDocument(pdf) as doc:
        return doc[0].render(scale=dpi / 72).to_pil().convert("RGB")


def as_pdf(image: Image.Image, dpi: int, quality: int) -> bytes:
    jpeg = io.BytesIO()
    image.save(jpeg, "JPEG", quality=quality)
    out = io.BytesIO()
    Image.open(jpeg).save(out, "PDF", resolution=dpi)
    return out.getvalue()


def photo(pdf: bytes, rng: random.Random) -> bytes:
    """A phone photo of the page on a desk: perspective, uneven light, warm tint, blur, JPEG 40."""
    page = render(pdf, 150)
    w, h = page.size
    desk = Image.new("RGB", (int(w * 1.12), int(h * 1.08)), (92, 74, 58))
    desk.paste(page, (int(w * 0.06), int(h * 0.04)))
    dw, dh = desk.size
    j = lambda: rng.uniform(0.0, 0.05)  # noqa: E731
    quad = (dw * j(), dh * j(), dw * j(), dh * (1 - j()), dw * (1 - j()), dh * (1 - j()), dw * (1 - j()), dh * j())
    shot = desk.transform((int(dw * 0.9), int(dh * 0.9)), Image.Transform.QUAD, quad, Image.Resampling.BICUBIC)
    arr = np.asarray(shot, dtype=np.float32)
    yy, xx = np.mgrid[0 : arr.shape[0], 0 : arr.shape[1]]
    light = 0.72 + 0.35 * (xx / arr.shape[1]) * (1 - 0.4 * yy / arr.shape[0])
    arr = arr * light[..., None] * np.array([1.0, 0.96, 0.88])
    shot = Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.1))
    return as_pdf(shot, 150, 40)


def fax(pdf: bytes, rng: random.Random) -> bytes:
    """A fax: 100 DPI, black and white, speckles, a slight tilt."""
    page = render(pdf, 100).convert("L").rotate(rng.uniform(-1.2, 1.2), fillcolor=255)
    arr = np.asarray(page, dtype=np.float32)
    arr += np.random.default_rng(rng.randint(0, 2**31)).normal(0, 30, arr.shape)
    bw = Image.fromarray(np.where(arr > 165, 255, 0).astype("uint8"))
    return as_pdf(bw.convert("RGB"), 100, 85)


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    GOLD.mkdir(exist_ok=True)
    for name, draw in DOCUMENTS.items():
        rng = random.Random(name)
        buffer = io.BytesIO()
        canvas = Canvas(buffer, pagesize=A4)
        page = Page(canvas)
        draw(page, rng)
        canvas.showPage()
        canvas.save()
        gold = {"values": page.values, "lines": page.lines, "tables": page.tables}
        variants = {f"{name}__digital": buffer.getvalue()}
        if name in SCANNED:
            variants[f"{name}__scan"] = scan(buffer.getvalue(), random.Random(f"{name}-scan"), 200)
        if name in LOW_RES:
            variants[f"{name}__lowres"] = scan(buffer.getvalue(), random.Random(f"{name}-low"), 110)
        if name in PHOTO:
            variants[f"{name}__photo"] = photo(buffer.getvalue(), random.Random(f"{name}-photo"))
        if name in FAX:
            variants[f"{name}__fax"] = fax(buffer.getvalue(), random.Random(f"{name}-fax"))
        for page_id, data in variants.items():
            (DOCS / f"{page_id}.pdf").write_bytes(data)
            (GOLD / f"{page_id}.json").write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(list(DOCS.glob('*.pdf')))} pages in {DOCS}")


if __name__ == "__main__":
    main()
