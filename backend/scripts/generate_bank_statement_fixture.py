"""Generate bank-statement.pdf: a fictional two-page statement for extraction tests."""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]  # backend/
OUT = ROOT.parent / "e2e" / "fixtures" / "documents" / "bank-statement.pdf"

HOLDER = "SARA EXEMPLE"
AGENCY = "CASA ANFA"
ACCOUNT = "007 780 0001234567890123 45"
OPENING = ("01/03/2025", 48_250.00)
CLOSING_DATE = "31/03/2025"
ROWS_PER_PAGE = 22

# (operation date, value date, description, amount, is_credit)
MOVEMENTS: list[tuple[str, str, str, float, bool]] = [
    ("01/03", "01/03", "PAIEMENT PAR CARTE MARJANE CASA", 845.30, False),
    ("02/03", "02/03", "RETRAIT CARTE GAB CASA ANFA", 1_000.00, False),
    ("02/03", "03/03", "PAIEMENT PAR CARTE PHARMACIE ATLAS", 212.40, False),
    ("03/03", "03/03", "RECHARGE TELEPHONE", 100.00, False),
    ("04/03", "04/03", "VIREMENT EMIS LOYER MARS", 6_500.00, False),
    ("05/03", "05/03", "RETRAIT PAR CHEQUE 0001245", 2_300.00, False),
    ("05/03", "05/03", "VERSEMENT DE ESPECES", 12_000.00, True),
    ("06/03", "06/03", "PAIEMENT PAR CARTE STATION AFRIQUIA", 450.00, False),
    ("07/03", "07/03", "FRAIS TENUE DE COMPTE", 25.00, False),
    ("07/03", "07/03", "PAIEMENT PAR CARTE CAFE DU PARC", 68.50, False),
    ("08/03", "08/03", "RETRAIT CARTE GAB MAARIF", 500.00, False),
    ("09/03", "10/03", "PAIEMENT PAR CARTE LIBRAIRIE CENTRALE", 189.90, False),
    ("10/03", "10/03", "VIREMENT EMIS FACTURE ELECTRICITE", 742.15, False),
    ("11/03", "11/03", "PAIEMENT PAR CARTE MARJANE CASA", 1_120.75, False),
    ("12/03", "12/03", "DROIT DE TIMBRE", 20.00, False),
    ("12/03", "12/03", "RETRAIT CARTE GAB CASA ANFA", 2_000.00, False),
    ("13/03", "13/03", "PAIEMENT PAR CARTE RESTAURANT LE JARDIN", 356.00, False),
    ("14/03", "14/03", "RECHARGE TELEPHONE", 50.00, False),
    ("15/03", "15/03", "VIREMENT EMIS ASSURANCE AUTO", 1_830.00, False),
    ("16/03", "17/03", "PAIEMENT PAR CARTE PHARMACIE ATLAS", 97.60, False),
    ("17/03", "17/03", "RETRAIT CARTE GAB MAARIF", 800.00, False),
    ("18/03", "18/03", "PAIEMENT PAR CARTE STATION AFRIQUIA", 520.00, False),
    ("19/03", "19/03", "PAIEMENT PAR CARTE CINEMA MEGARAMA", 140.00, False),
    ("20/03", "20/03", "FRAIS VIREMENT", 15.00, False),
    ("20/03", "20/03", "VERSEMENT DE SALAIRE MARS", 18_500.00, True),
    ("21/03", "21/03", "VIREMENT EMIS ECOLE PRIVEE", 3_200.00, False),
    ("22/03", "22/03", "PAIEMENT PAR CARTE MARJANE CASA", 963.20, False),
    ("23/03", "24/03", "RETRAIT CARTE GAB CASA ANFA", 1_500.00, False),
    ("24/03", "24/03", "PAIEMENT PAR CARTE OPTICIEN VISION", 650.00, False),
    ("25/03", "25/03", "VIREMENT EMIS FACTURE EAU", 238.45, False),
    ("25/03", "25/03", "PAIEMENT PAR CARTE CAFE DU PARC", 42.00, False),
    ("26/03", "26/03", "RETRAIT PAR CHEQUE 0001246", 1_250.00, False),
    ("27/03", "27/03", "PAIEMENT PAR CARTE BOULANGERIE AMAL", 76.30, False),
    ("27/03", "27/03", "RECHARGE TELEPHONE", 100.00, False),
    ("28/03", "28/03", "PAIEMENT PAR CARTE STATION AFRIQUIA", 480.00, False),
    ("29/03", "29/03", "RETRAIT CARTE GAB MAARIF", 700.00, False),
    ("30/03", "30/03", "PAIEMENT PAR CARTE PRESSING CENTRAL", 85.00, False),
    ("31/03", "31/03", "FRAIS TENUE DE COMPTE", 25.00, False),
    ("31/03", "31/03", "DROIT DE TIMBRE", 20.00, False),
    ("31/03", "31/03", "PAIEMENT PAR CARTE MARJANE CASA", 731.85, False),
]


def money(value: float) -> str:
    whole, cents = f"{value:.2f}".split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    return f"{' '.join(groups)},{cents}"


def row_line(op: str, val: str, desc: str, amount: float, is_credit: bool) -> str:
    debit = "" if is_credit else money(amount)
    credit = money(amount) if is_credit else ""
    return f"{op}  {val}  {desc:<40}{debit:>12}  {credit:>12}"


def header(page: pymupdf.Page, number: int, total: int) -> float:
    lines = [
        "BANQUE EXEMPLE",
        f"RELEVE DE COMPTE                                          PAGE {number}/{total}",
        "",
        f"TITULAIRE : {HOLDER}",
        f"AGENCE : {AGENCY}",
        f"NUMERO DE COMPTE : {ACCOUNT}",
        "DEVISE : MAD",
        "",
        f"{'OPER':<5}  {'VALEUR':<5}  {'LIBELLE':<40}{'DEBIT':>12}  {'CREDIT':>12}",
    ]
    y = 60.0
    for line in lines:
        page.insert_text((40, y), line, fontname="cour", fontsize=8.5)
        y += 13
    return y


def build() -> bytes:
    debit_total = round(sum(a for *_, a, credit in MOVEMENTS if not credit), 2)
    credit_total = round(sum(a for *_, a, credit in MOVEMENTS if credit), 2)
    closing = round(OPENING[1] + credit_total - debit_total, 2)
    pages = [MOVEMENTS[i : i + ROWS_PER_PAGE] for i in range(0, len(MOVEMENTS), ROWS_PER_PAGE)]

    doc = pymupdf.open()
    for index, rows in enumerate(pages, start=1):
        page = doc.new_page(width=595, height=842)
        y = header(page, index, len(pages))
        if index == 1:
            line = f"SOLDE DEPART AU : {OPENING[0]}  {money(OPENING[1])}"
            page.insert_text((40, y), line, fontname="cour", fontsize=8.5)
            y += 13
        for row in rows:
            page.insert_text((40, y), row_line(*row), fontname="cour", fontsize=8.5)
            y += 13
        if index == len(pages):
            y += 13
            footer = [
                f"{'TOTAL DES MOUVEMENTS':<54}{money(debit_total):>12}  {money(credit_total):>12}",
                f"NOUVEAU SOLDE AU : {CLOSING_DATE}  {money(closing)}",
            ]
            for line in footer:
                page.insert_text((40, y), line, fontname="cour", fontsize=8.5)
                y += 13
    data = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return data


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(build())
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
