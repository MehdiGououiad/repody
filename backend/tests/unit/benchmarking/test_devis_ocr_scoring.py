"""Unit tests for Hôpital Privé Agadir devis OCR markdown scoring (hard + ICE)."""

from __future__ import annotations

import pytest

from repody.benchmarking import hit_field, score_devis_markdown

GOLDEN_MARKDOWN = """
HOPITAL PRIVE AGADIR
DEVIS
PRESTATIONS
REANIMATION ADULTE 29 3 000,00 87 000,00
OXYGENE 1 188 500,00 188 500,00
Sous-Total 416 050,00
HONORAIRES
Dr. LAHYAT / ABBASSI 54 000,00
Sous-Total 58 000,00
LABORATOIRE
LABO 23 500,00
Sous-Total 23 500,00
Total devis 497 550,00
QUATRE CENT QUATRE-VINGT-DIX-SEPT MILLE CINQ CENT CINQUANTE DIRHAMS
ICE 001639657000061 INPE 040063554
CNSS 1050899 PATENTE 49297765 IF 18818720
"""


def test_ice_hit_on_golden_markdown():
    result = score_devis_markdown(GOLDEN_MARKDOWN)
    assert result["ice_hit"] is True
    assert result["hits"]["ice"] is True


def test_ice_missing_fails():
    bad = GOLDEN_MARKDOWN.replace("001639657000061", "001639657000060")
    result = score_devis_markdown(bad)
    assert result["ice_hit"] is False
    assert result["hits"]["ice"] is False


def test_ice_requires_full_digit_sequence():
    partial = GOLDEN_MARKDOWN.replace("001639657000061", "00163965700006")
    assert score_devis_markdown(partial)["hits"]["ice"] is False


def test_total_devis_amount_hit():
    result = score_devis_markdown(GOLDEN_MARKDOWN)
    assert result["hits"]["total_devis"] is True


def test_hard_subtotals_and_footer_ids():
    result = score_devis_markdown(GOLDEN_MARKDOWN)
    assert result["hits"]["subtotal_prestations"] is True
    assert result["hits"]["subtotal_honoraires"] is True
    assert result["hits"]["subtotal_laboratoire"] is True
    assert result["hits"]["inpe"] is True
    assert result["hits"]["cnss"] is True
    assert result["hits"]["patente"] is True
    assert result["hits"]["if_tax"] is True


def test_core_only_scoring_excludes_hard_fields():
    result = score_devis_markdown(GOLDEN_MARKDOWN, include_hard=False)
    assert result["hard_max"] == 0
    assert result["core_score"] >= 6
    assert result["core_max"] == 7


def test_empty_markdown_scores_zero():
    result = score_devis_markdown("")
    assert result["total_score"] == 0
    assert result["ice_hit"] is False


@pytest.mark.parametrize(
    ("compare", "expected", "text", "want"),
    [
        ("digits", "001639657000061", "ICE: 001 639 657 000 061", True),
        ("digits", "001639657000061", "001639657000060", False),
        ("amount", "497550", "Total devis 497 550,00 DH", True),
        ("contains", "DEVIS", "Document: DEVIS patient", True),
    ],
)
def test_hit_field_comparators(compare: str, expected: str, text: str, want: bool):
    assert hit_field(text, {"compare": compare, "expected": expected}) is want
