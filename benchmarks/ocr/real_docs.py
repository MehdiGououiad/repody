# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=13.0"]
# ///
"""Real French documents with a hand-written gold, copied into docs/ as PNG (same pixels, alpha on white).

    uv run real_docs.py

Fixtures come from e2e/fixtures/documents; the others are downloaded from Wikimedia Commons (licence
next to each). The gold lists only text that is legible with certainty; for handwriting it keeps the
words as written. Pages end in `__real`, which score.py reports as their own column.
"""

from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parents[1] / "e2e" / "fixtures" / "documents"
COMMONS = "https://upload.wikimedia.org/wikipedia/commons/"
THUMBS = "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
UA = {"User-Agent": "RepodyOCRBench/1.0 (document OCR benchmark)"}

DOCUMENTS = {
    # e2e fixture: a French payslip template (890 x 1105 px), printed.
    "fiche": {
        "source": FIXTURES / "fiche.webp",
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
        "tables": [[
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
        ]],
    },
    # e2e fixture: a printed repair-invoice form filled in by hand.
    "retouche": {
        "source": FIXTURES / "Facture RETOUCHE remplie AVEC TVA.png",
        "values": ["027", "30/06/24", "8H20", "123 456 789 10101", "16,80€", "28,80€", "38€", "7,60€",
                   "45,60€", "19€", "26,60€", "14€", "12€"],
        "lines": [
            "FACTURE RETOUCHE", "BINET COUTURE", "6 RUE DE LA RETOUCHE", "29 350 MOËLAN-SUR-MER", "MME DU TOIT",
            "RÉPARATIONS ÉLIGIBLES AU BONUS RÉPARATION", "RÉPARATIONS NON ÉLIGIBLES AU BONUS RÉPARATION",
            "TROU, ACCROC, DÉCHIRURE", "CHANGEMENT DOUBLURE", "CHANGEMENT DE ZIP", "OPÉRATION COUTURE",
            "TVA non applicable, article 293 B du Code général des impôts", "TOTAL BONUS RÉPARATION",
            "NET À PAYER", "VOTRE ARTISAN S'ENGAGE À UNE GARANTIE DE 3 MOIS SUR LES RÉPARATIONS FAITES",
        ],
        "tables": [[["1", "14€", "16,80€"], ["2", "12€", "28,80€"]]],
    },
    # e2e fixture: a handwritten invoice book page with a shop stamp and a diagonal "Exemple".
    "asiahome": {
        "source": FIXTURES / "facturehandwritten.png",
        "values": ["19/02/2017", "47,23", "6,65", "53,88", "2,50", "1,99", "1,50", "2,99"],
        "lines": ["ASIA HOME", "1720, Avenue de l'Europe", "34170 CASTELNAU LE LEZ", "FACTURE", "Spoutnik",
                  "34000 Montpellier", "Revue", "Sauce Soja", "Nems frais", "EVENTAIL", "Exemple"],
        "tables": [],
    },
    # Wikimedia Commons, public domain: a faded, folded C&A till receipt (1981), dot-matrix in purple.
    "canda": {
        "source": COMMONS + "0/0a/Ticket_de_caisse_d%27un_magasin_de_v%C3%AAtements_C%26A.jpg",
        "values": ["450.00", "095.00", "220.00", "099.00", "190.00", "1.054.00", "1860", "1864", "1868"],
        "lines": ["TOUTE LA MODE POUR", "FEMMES HOMMES ET ENFANTS", "Echange ou Remboursement",
                  "Ticket exigé - délai 15 jours"],
        "tables": [],
    },
    # Wikimedia Commons, CC BY-SA 4.0: a 1968 rent receipt, cursive print filled in by hand.
    "quittance1968": {
        "source": THUMBS + "9/97/Quittance_de_loyer_%281968%29.jpg/1920px-Quittance_de_loyer_%281968%29.jpg",
        "values": ["250", "15 Octobre 1968", "15 Novembre 1968"],
        "lines": ["QUITTANCE DE LOYER", "Reçu de Monsieur", "la somme de", "pour le montant d'un",
                  "de loyer des locaux qu'il", "occupe dans la maison située", "commençant le", "et finissant",
                  "sous toutes réserves de droit", "DONT QUITTANCE", "Un locataire ne peut déménager",
                  "Loyer", "Concierge", "Eclairage", "Timbre", "Eau", "Total", "Meublé", "Jean Jaurès"],
        "tables": [],
    },
    # Wikimedia Commons, CC0 (Paris Musées): a 1921 invoice, handwritten lines, stamp, pencil notes.
    "babani": {
        "source": THUMBS + "c/c6/Facture%2C_2016.3.1.jpg/1920px-Facture%2C_2016.3.1.jpg",
        "values": ["26 Août 1921", "1100", "2200", "2201", "2202", "27-53"],
        "lines": ["BABANI", "98 Boul. Haussmann", "KIMONOS", "ETOFFES", "ROBES", "d'ORIENT",
                  "Robe Crétoise velours noir", "naziade marine et or", "timbre", "Pour acquit",
                  "Imp. Tolmer & Cie - Paris", "Tél. Louvre 27-53", "6 Rue Halévy",
                  "Passé le délai de 24 heures, aucune marchandise ne sera reprise ni échangée"],
        "tables": [[["1", "Robe Crétoise velours noir", "1100"], ["1", "naziade marine et or", "1100"]]],
    },
    # Wikimedia Commons, public domain: an 1832 coal delivery note, engraved cursive and ink handwriting.
    "vigan": {
        "source": THUMBS + "f/f8/Bon_de_livraison_Mines_de_Houille_de_Vigan.jpg/1920px-Bon_de_livraison_Mines_de_Houille_de_Vigan.jpg",
        "values": ["784", "1832", "18 avril"],
        "lines": ["Mines de Houille du Vigan", "Il a été délivré au", "la quantité de", "Bènes de Houille",
                  "la voiture à raison de", "centimes, le quintal ancien poids", "La lettre de voiture sous le",
                  "en date du", "a été expédiée par la poste", "à Monsieur", "Fontane", "Gange", "Barral"],
        "tables": [],
    },
    # Supplied by the user (save as e2e/fixtures/documents/espace-transit-facture.png or .jpg): a dense
    # Moroccan customs-broker invoice in French, small type, ruled boxes, bank details.
    "espacetransit": {
        "source": next(iter(sorted(FIXTURES.glob("espace-transit-facture.*"))), FIXTURES / "espace-transit-facture.png"),
        "values": ["17/05/2021", "C21005099", "342123330", "CASOI21005079", "10/62367F", "08/05/2021",
                   "525 940,00", "20 899,76", "319 540,16", "DEB127", "105 453,00", "106 920,00",
                   "000 068 00 051970 32", "SGMBMAMC068", "001524191000063", "F.L.12795", "001529406000005",
                   "+212.522.317.473", "+212.522.316.858", "32179551", "2105650", "01600966"],
        "lines": ["ESPACE TRANSIT", "Votre lien logistique au Maroc", "RELEVE D'IDENTITE BANCAIRE",
                  "BANQUE : S.G.M.B", "AGENCE : TZ EMILE ZOLA", "CODE SWIFT : SGMBMAMC068",
                  "Casablanca, le 17/05/2021", "SCHENKER MAROC", "PC ACTIVITE OUKACHA 3 TR BAT 1& 2",
                  "BD MLY SLIMANE CASABLANCA", "FACTURE N° : C21005099", "Droits de douane", "HENKEL",
                  "Arrêtée la présente facture à la somme de :", "Cent six mille neuf cent vingt DHS",
                  "PIECES JOINTES", "TICKET DE PAIEMENT", "NET A PAYER", "ESPACE TRANSIT S.A.R.L.",
                  "25 rue Karatchi", "20110 Casablanca", "financier@espacetransit.com", "www.espacetransit.com"],
        "tables": [[["DEB127", "Droits de douane", "105 453,00", "106 920,00"],
                    ["022", "780", "000 068 00 051970 32", "74"]]],
    },
}


def load(source: Path | str) -> Image.Image:
    if isinstance(source, Path):
        return Image.open(source)
    with urllib.request.urlopen(urllib.request.Request(source, headers=UA)) as response:
        return Image.open(io.BytesIO(response.read()))


def main() -> None:
    (HERE / "docs").mkdir(exist_ok=True)
    (HERE / "gold").mkdir(exist_ok=True)
    for name, doc in DOCUMENTS.items():
        page = HERE / "docs" / f"{name}__real.png"
        if isinstance(doc["source"], Path) and not doc["source"].exists():
            print(f"skipped {name}: {doc['source']} is missing")
            continue
        if not page.exists():
            image = load(doc["source"]).convert("RGBA")
            flat = Image.new("RGB", image.size, "white")
            flat.paste(image, mask=image.getchannel("A"))
            flat.save(page)
        gold = {k: doc[k] for k in ("values", "lines", "tables")}
        (HERE / "gold" / f"{name}__real.json").write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")
        print(page.name)


if __name__ == "__main__":
    main()
