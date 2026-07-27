"""Generic OCR markdown scorer driven by fixture expectations JSON."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from audit_workbench.benchmarking.text import digits_only, normalize_space, parse_amount

_FIXTURES_ROOT = Path(__file__).resolve().parents[4] / "e2e" / "fixtures" / "documents"


def hit_field(text: str, field: dict[str, Any]) -> bool:
    compare = str(field.get("compare") or "contains")
    expected = field.get("expected")
    if expected is None:
        return False
    if compare == "digits":
        needle = digits_only(expected)
        return bool(needle) and needle in digits_only(text)
    if compare == "amount":
        expected_amount = parse_amount(expected)
        if expected_amount is None:
            return False
        for token in re.findall(r"[\d\s.,]+", text):
            amount = parse_amount(token)
            if amount is not None and amount == expected_amount:
                return True
        compact = digits_only(expected)
        return bool(compact) and compact in digits_only(text)
    if compare == "contains":
        return normalize_space(expected) in normalize_space(text)
    return normalize_space(expected) == normalize_space(text)


def load_expectations(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score_fixture_markdown(
    text: str,
    expectations: dict[str, Any],
    *,
    include_hard: bool = True,
) -> dict[str, Any]:
    core = expectations.get("core_fields") or []
    hard = expectations.get("hard_fields") or [] if include_hard else []
    primary = str(expectations.get("primary_hit") or "primary")

    hits: dict[str, bool] = {}
    weights: dict[str, int] = {}
    for field in core + hard:
        field_id = str(field["id"])
        hits[field_id] = hit_field(text, field)
        weights[field_id] = int(field.get("weight") or 1)

    core_score = sum(weights[f["id"]] for f in core if hits.get(f["id"]))
    core_max = sum(int(f.get("weight") or 1) for f in core)
    hard_score = sum(weights[f["id"]] for f in hard if hits.get(f["id"]))
    hard_max = sum(int(f.get("weight") or 1) for f in hard)

    return {
        "fixture_id": expectations.get("fixture_id"),
        "core_score": core_score,
        "core_max": core_max,
        "hard_score": hard_score,
        "hard_max": hard_max,
        "total_score": core_score + hard_score,
        "total_max": core_max + hard_max,
        "primary_hit": hits.get(primary, False),
        "primary_field": primary,
        "hits": hits,
        "weights": weights,
        "chars": len(text),
    }


def _side_signal(text: str, side: str) -> int:
    folded = normalize_space(text)
    if side == "front":
        score = 0
        if "carte nationale" in folded:
            score += 4
        if "royaume du maroc" in folded or "royalme du maroc" in folded:
            score += 3
        if "valable" in folded or "can " in folded:
            score += 2
        if "idmar" in folded or "fils de" in folded or "filsde" in folded:
            score -= 4
        if "adresse" in folded or "ziraoui" in folded:
            score -= 2
        return score
    score = 0
    if "idmar" in folded:
        score += 4
    if "fils de" in folded or "filsde" in folded:
        score += 3
    if "adresse" in folded or "ziraoui" in folded:
        score += 2
    if "gououiad<<" in folded or "gououiad<<" in text.lower():
        score += 2
    if "carte nationale" in folded:
        score -= 4
    if "valable" in folded:
        score -= 2
    return score


def orient_cnie_sides(front_text: str, back_text: str) -> tuple[str, str]:
    normal = _side_signal(front_text, "front") + _side_signal(back_text, "back")
    swapped = _side_signal(back_text, "front") + _side_signal(front_text, "back")
    if swapped > normal:
        return back_text, front_text
    return front_text, back_text


def score_cnie_pair(
    front_text: str,
    back_text: str,
    spec: dict[str, Any],
    *,
    include_hard: bool = True,
) -> dict[str, Any]:
    front_text, back_text = orient_cnie_sides(front_text, back_text)
    front = score_fixture_markdown(front_text, spec["front"], include_hard=include_hard)
    back = score_fixture_markdown(back_text, spec["back"], include_hard=include_hard)

    hits = {f"front_{k}": v for k, v in front["hits"].items()}
    hits.update({f"back_{k}": v for k, v in back["hits"].items()})

    return {
        "fixture_id": spec.get("fixture_id"),
        "front_score": front["total_score"],
        "front_max": front["total_max"],
        "back_score": back["total_score"],
        "back_max": back["total_max"],
        "core_score": front["core_score"] + back["core_score"],
        "core_max": front["core_max"] + back["core_max"],
        "hard_score": front["hard_score"] + back["hard_score"],
        "hard_max": front["hard_max"] + back["hard_max"],
        "total_score": front["total_score"] + back["total_score"],
        "total_max": front["total_max"] + back["total_max"],
        "cin_hit": front["hits"].get("national_id", False),
        "mrz_hit": back["hits"].get("mrz_line1_prefix", False),
        "primary_hit": front["hits"].get("national_id", False)
        and back["hits"].get("mrz_line1_prefix", False),
        "hits": hits,
        "front_chars": front["chars"],
        "back_chars": back["chars"],
        "chars": front["chars"] + back["chars"],
    }


def _fixture_path(name: str) -> Path:
    return _FIXTURES_ROOT / name


@lru_cache(maxsize=4)
def _load_named_expectations(name: str) -> dict[str, Any]:
    return json.loads(_fixture_path(name).read_text(encoding="utf-8"))


def score_devis_markdown(text: str, *, include_hard: bool = True) -> dict[str, Any]:
    scored = score_fixture_markdown(
        text,
        _load_named_expectations("hopital-devis-agadir.ocr-expectations.json"),
        include_hard=include_hard,
    )
    scored["ice_hit"] = bool(scored.get("hits", {}).get("ice"))
    return scored


def score_att_salaire_markdown(text: str, *, include_hard: bool = True) -> dict[str, Any]:
    scored = score_fixture_markdown(
        text,
        _load_named_expectations("att-salaire.ocr-expectations.json"),
        include_hard=include_hard,
    )
    scored["cin_hit"] = scored.get("primary_hit", False)
    return scored


def score_gououiad_cnie_markdown(
    front_text: str,
    back_text: str,
    *,
    include_hard: bool = True,
) -> dict[str, Any]:
    return score_cnie_pair(
        front_text,
        back_text,
        _load_named_expectations("gououiad-cnie.ocr-expectations.json"),
        include_hard=include_hard,
    )


def score_fixture_fields(
    fields: dict[str, str],
    expectations: dict[str, Any],
    *,
    include_hard: bool = True,
) -> dict[str, Any]:
    """Score structured extraction values keyed by expectation field id."""
    core = expectations.get("core_fields") or []
    hard = expectations.get("hard_fields") or [] if include_hard else []
    primary = str(expectations.get("primary_hit") or "primary")

    hits: dict[str, bool] = {}
    weights: dict[str, int] = {}
    for field in core + hard:
        field_id = str(field["id"])
        hits[field_id] = hit_field(str(fields.get(field_id) or ""), field)
        weights[field_id] = int(field.get("weight") or 1)

    core_score = sum(weights[f["id"]] for f in core if hits.get(f["id"]))
    core_max = sum(int(f.get("weight") or 1) for f in core)
    hard_score = sum(weights[f["id"]] for f in hard if hits.get(f["id"]))
    hard_max = sum(int(f.get("weight") or 1) for f in hard)

    return {
        "fixture_id": expectations.get("fixture_id"),
        "core_score": core_score,
        "core_max": core_max,
        "hard_score": hard_score,
        "hard_max": hard_max,
        "total_score": core_score + hard_score,
        "total_max": core_max + hard_max,
        "primary_hit": hits.get(primary, False),
        "primary_field": primary,
        "hits": hits,
        "weights": weights,
        "fields": {k: fields.get(k, "") for k in hits},
    }


def score_cnie_field_pair(
    front_fields: dict[str, str],
    back_fields: dict[str, str],
    spec: dict[str, Any],
    *,
    include_hard: bool = True,
) -> dict[str, Any]:
    front = score_fixture_fields(front_fields, spec["front"], include_hard=include_hard)
    back = score_fixture_fields(back_fields, spec["back"], include_hard=include_hard)

    hits = {f"front_{k}": v for k, v in front["hits"].items()}
    hits.update({f"back_{k}": v for k, v in back["hits"].items()})

    return {
        "fixture_id": spec.get("fixture_id"),
        "front_score": front["total_score"],
        "front_max": front["total_max"],
        "back_score": back["total_score"],
        "back_max": back["total_max"],
        "core_score": front["core_score"] + back["core_score"],
        "core_max": front["core_max"] + back["core_max"],
        "hard_score": front["hard_score"] + back["hard_score"],
        "hard_max": front["hard_max"] + back["hard_max"],
        "total_score": front["total_score"] + back["total_score"],
        "total_max": front["total_max"] + back["total_max"],
        "cin_hit": front["hits"].get("national_id", False),
        "mrz_hit": back["hits"].get("mrz_line1_prefix", False),
        "primary_hit": front["hits"].get("national_id", False)
        and back["hits"].get("mrz_line1_prefix", False),
        "hits": hits,
        "front_fields": front["fields"],
        "back_fields": back["fields"],
    }


def score_gououiad_cnie_fields(
    front_fields: dict[str, str],
    back_fields: dict[str, str],
    *,
    include_hard: bool = True,
) -> dict[str, Any]:
    return score_cnie_field_pair(
        front_fields,
        back_fields,
        _load_named_expectations("gououiad-cnie.ocr-expectations.json"),
        include_hard=include_hard,
    )
