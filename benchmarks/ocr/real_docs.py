# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=13.0"]
# ///
"""Real documents with a hand-written gold: copied into docs/ as PNG (same pixels, alpha on white).

    uv run real_docs.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parents[1] / "e2e" / "fixtures" / "documents"

# e2e/fixtures/documents/fiche.webp: a French payslip (890 x 1105 px).
FICHE = {
    "values": [
        "99999999900099", "4331Z", "79448723100019", "2198", "000000000000000", "15/03/2019", "3 925,00€",
        "01/03/2025", "31/03/2025", "23,08€", "3 500,00€", "245,00€", "77,70€", "241,50€", "299,25€",
        "14,00€", "70,70€", "30,10€", "45,15€", "110,25€", "165,20€", "120,75€", "141,75€", "8,75€",
        "3 438,75€", "233,84€", "73,36€", "629,69€", "1 247,61€", "99,72€", "2 770,59€", "51,79€",
        "151,67", "455,01", "10 500,00€", "1 877,30€", "8 610,93€", "4 747,61€", "2 870,31€", "100,46€",
        "301,38€", "3,50 %", "2 670,13€",
    ],
    "lines": [
        "VOTRE ENTREPRISE", "35 Allée de la Mairie", "44300 NANTES", "Fiche de paie",
        "Période du : 01/03/2025 au : 31/03/2025", "Paiement le : 31/03/2025", "VOTRE SALARIÉ",
        "31 rue Jean THEUVENEY", "Siret : 99999999900099", "Code NAF : 4331Z", "Urssaf : 79448723100019",
        "Convention : 2198 - Convention collective nationale des entreprises de vente à distance",
        "Matricule : 1", "N° Sécurité Sociale : 000000000000000", "Entrée le : 15/03/2019", "Emploi : Soudeur",
        "Qualification : Non cadre", "Coefficient : 100", "Plafond Sécurité Sociale : 3 925,00€", "Contrat : cdi",
        "MONTANT NET SOCIAL", "NET À PAYER AVANT IMPOT SUR LE REVENU",
        "Dont évolution de la rémunération liée à la suppression des cotisations chômage et maladie",
        "Montant net imposable", "Impôt sur le revenu prélevé à la source",
        "Montant net des heures compl/suppl exonérées", "Congés Payés", "Net à payer au salarié",
        "Bulletin de paie simplifié - Normes en vigueur",
    ],
    "tables": [
        [
            ["Rubriques", "Base", "Taux Salarial", "Cot. Salariales", "Taux Patronal", "Cot. Patronales"],
            ["SALAIRE DE BASE ( 23,08€/h )", "3 500,00€"],
            ["SALAIRE BRUT", "3 500,00€"],
            ["Sécurité sociale", "3 500,00€", "7,00", "245,00€"],
            ["ACCIDENTS DU TRAVAIL - MALADIES PROFESSIONNELLES", "3 500,00€", "2,22", "77,70€"],
            ["Assurance Vieillesse plafonnée", "3 500,00€", "6,90", "241,50€", "8,55", "299,25€"],
            ["Assurance Vieillesse déplafonnée", "3 500,00€", "0,40", "14,00€", "2,02", "70,70€"],
            ["CEG tranche 1", "3 500,00€", "0,86", "30,10€", "1,29", "45,15€"],
            ["Retraite complémentaire tranche 1 AGIRC-ARRCO", "3 500,00€", "3,15", "110,25€", "4,72", "165,20€"],
            ["FAMILLE - SÉCURITÉ SOCIALE", "3 500,00€", "120,75€"],
            ["Assurance chômage tranche A", "3 500,00€", "4,05", "141,75€"],
            ["Assurance chômage tranche AGS (FNGS)", "3 500,00€", "0,25", "8,75€"],
            ["CSG déductible", "3 438,75€", "6,80", "233,84€"],
            ["AUTRES CONTRIBUTIONS DUES PAR L'EMPLOYEUR", "3 500,00€", "73,36€"],
            ["TOTAL DES RETENUES", "629,69€", "1 247,61€"],
            ["CSG/CRDS imposable à l'impôt sur le revenu", "3 438,75€", "2,90", "99,72€", "0,00€"],
            ["MONTANT NET SOCIAL", "2 770,59€"],
        ]
    ],
}


def main() -> None:
    image = Image.open(FIXTURES / "fiche.webp").convert("RGBA")
    flat = Image.new("RGB", image.size, "white")
    flat.paste(image, mask=image.getchannel("A"))
    flat.save(HERE / "docs" / "fiche__real.png")
    (HERE / "gold" / "fiche__real.json").write_text(json.dumps(FICHE, ensure_ascii=False, indent=1), encoding="utf-8")
    print("docs/fiche__real.png")


if __name__ == "__main__":
    main()
