"""Unit tests for Gououiad CNIE recto+verso OCR scoring."""

from __future__ import annotations

from audit_workbench.benchmarking import (
    score_gououiad_cnie_fields,
    score_gououiad_cnie_markdown,
)

FRONT = """
ROYAUME DU MAROC
CARTE NATIONALE D'IDENTITE
MEHDI GOUOUIAD
N° BE899456
Né le 24.02.1998 à HAY HASSANI
Valable jusqu'au 04.08.2035
CAN 373473
مهدي
"""

BACK = """
N° BE899456
Fils de MOHAMED ben M'BAREK
Et de KHADDOUJ bent ABDELKBIR
Adresse 125 BD ZIRAOUI CASABLANCA
Sexe M
OPIEMD92
IDMAROPIEMD92<7BE899456<<<<<<
9802241M3508046MAR<<<<<<<<<<<2
GOUOUIAD<<MEHDI<<<<<<<<<<<<<<<
"""


def test_full_pair_scores_high():
    result = score_gououiad_cnie_markdown(FRONT, BACK)
    assert result["cin_hit"] is True
    assert result["mrz_hit"] is True
    assert result["total_score"] >= result["total_max"] - 2


def test_wrong_cin_fails():
    bad_front = FRONT.replace("BE899456", "BE899457")
    result = score_gououiad_cnie_markdown(bad_front, BACK)
    assert result["cin_hit"] is False


def test_missing_mrz_fails():
    bad_back = BACK.replace("IDMAROPIEMD92", "IDMARXXXXXX")
    result = score_gououiad_cnie_markdown(FRONT, bad_back)
    assert result["mrz_hit"] is False


def test_front_core_fields():
    result = score_gououiad_cnie_markdown(FRONT, BACK)
    assert result["hits"]["front_first_name"] is True
    assert result["hits"]["front_valid_2035"] is True
    assert result["hits"]["front_can_serial"] is True


def test_back_parent_and_mrz_fields():
    result = score_gououiad_cnie_markdown(FRONT, BACK)
    assert result["hits"]["back_father_name"] is True
    assert result["hits"]["back_mother_name"] is True
    assert result["hits"]["back_mrz_line3_name"] is True


def test_orient_swaps_reversed_pair():
    result = score_gououiad_cnie_markdown(BACK, FRONT)
    assert result["cin_hit"] is True
    assert result["hits"]["front_first_name"] is True
    assert result["hits"]["back_father_name"] is True


def test_structured_fields_score():
    front = {
        "national_id": "BE899456",
        "first_name": "MEHDI",
        "last_name": "GOUOUIAD",
        "dob_1998": "1998",
        "dob_full": "24.02.1998",
        "valid_2035": "04.08.2035",
        "can_serial": "373473",
        "birth_place": "HAY HASSANI",
        "document_title": "CARTE NATIONALE D'IDENTITE",
        "kingdom_header": "ROYAUME DU MAROC",
        "arabic_first": "مهدي",
    }
    back = {
        "national_id": "BE899456",
        "father_name": "MOHAMED",
        "mother_name": "KHADDOUJ",
        "address_city": "CASABLANCA",
        "address_street": "ZIRAOUI",
        "gender": "M",
        "mrz_line1_prefix": "IDMAROPIEMD92",
        "mrz_line2_dob": "980224",
        "mrz_line2_expiry": "350804",
        "mrz_line3_name": "GOUOUIAD<<MEHDI",
        "opi_code": "OPIEMD92",
        "etat_civil": "143",
        "address_number": "125",
    }
    result = score_gououiad_cnie_fields(front, back)
    assert result["cin_hit"] is True
    assert result["mrz_hit"] is True
    assert result["total_score"] == result["total_max"]
