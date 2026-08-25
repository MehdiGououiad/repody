"""Benchmark suite scoring and OCR fixture scorers."""

from scripts.benchmarking.ocr import (
    hit_field,
    load_expectations,
    orient_cnie_sides,
    score_att_salaire_markdown,
    score_cnie_field_pair,
    score_cnie_pair,
    score_devis_markdown,
    score_fixture_fields,
    score_fixture_markdown,
    score_gououiad_cnie_fields,
    score_gououiad_cnie_markdown,
)
from scripts.benchmarking.suite import (
    compare_value,
    csv_report,
    html_report,
    normalize_text,
    score_fields,
    score_rules,
)
from scripts.benchmarking.text import digits_only, normalize_space, parse_amount

__all__ = [
    "compare_value",
    "csv_report",
    "digits_only",
    "hit_field",
    "html_report",
    "load_expectations",
    "normalize_space",
    "normalize_text",
    "orient_cnie_sides",
    "parse_amount",
    "score_att_salaire_markdown",
    "score_cnie_field_pair",
    "score_cnie_pair",
    "score_devis_markdown",
    "score_fields",
    "score_fixture_fields",
    "score_fixture_markdown",
    "score_gououiad_cnie_fields",
    "score_gououiad_cnie_markdown",
    "score_rules",
]
