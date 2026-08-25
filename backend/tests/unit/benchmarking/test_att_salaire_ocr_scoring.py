"""Unit tests for Att Salaire OCR markdown scoring."""

from __future__ import annotations

import pytest
from scripts.benchmarking import hit_field, score_att_salaire_markdown

GOLDEN = """
ROYAUME DU MAROC
MINISTERE DE L'ECONOMIE ET FINANCES
ATTESTATION DE SALAIRE
NUM. C.I.N. BE766480 MATRICULE 1447540
NOM PRENOM BOUHNIN MOHAMED
DATE DE NAISSANCE 31/10/1981 ECHELON 07 INDICE 542
TRAITEMENT DE BASE 2 818,89
BRUT MENSUEL 14 797,72
TOTAL RETENUES 4 003,50
BASE IMPOSABLE MENSUEL 2 494,37
NET MENSUEL 10 794,22
Rabat le 13/10/2023
Mohammed BOUAOUDA
"""


def test_cin_hit_on_golden():
    result = score_att_salaire_markdown(GOLDEN)
    assert result["cin_hit"] is True
    assert result["hits"]["national_id"] is True


def test_net_and_gross_amounts():
    result = score_att_salaire_markdown(GOLDEN)
    assert result["hits"]["net_monthly"] is True
    assert result["hits"]["gross_monthly"] is True


def test_hard_fields_on_golden():
    result = score_att_salaire_markdown(GOLDEN)
    assert result["hits"]["matricule"] is True
    assert result["hits"]["total_deductions"] is True
    assert result["hits"]["taxable_base"] is True
    assert result["hits"]["signatory"] is True


def test_wrong_cin_fails():
    bad = GOLDEN.replace("BE766480", "BE766481")
    assert score_att_salaire_markdown(bad)["cin_hit"] is False


@pytest.mark.parametrize(
    ("compare", "expected", "text", "want"),
    [
        ("contains", "BE766480", "CIN BE766480 matricule", True),
        ("amount", "10794.22", "NET MENSUEL 10 794,22", True),
        ("digits", "1447540", "MATRICULE 1 447 540", True),
    ],
)
def test_hit_field_comparators(compare: str, expected: str, text: str, want: bool):
    assert hit_field(text, {"compare": compare, "expected": expected}) is want
