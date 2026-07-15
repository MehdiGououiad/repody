"""Strict extraction assertions for CIH relevé NuExtract field types."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from audit_workbench.extraction.base import ExtractedFieldResult
from audit_workbench.extraction.field_json import normalize_amount, parse_numeric_value
from audit_workbench.rules.value_coercion import is_iso_date_like

from tests.fixtures.cih_releve_ground_truth import CihReleveGroundTruth

_DATE_DD_MM = re.compile(r"^\d{2}/\d{2}$")
_DATE_DD_MM_YYYY = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def field_map(fields: list[ExtractedFieldResult]) -> dict[str, ExtractedFieldResult]:
    return {field.key: field for field in fields}


def require_field(fields: list[ExtractedFieldResult], name: str) -> ExtractedFieldResult:
    hit = field_map(fields).get(name)
    if hit is None:
        raise AssertionError(f"missing field {name!r}")
    if not hit.extracted or hit.value in ("", "—"):
        raise AssertionError(f"field {name!r} not extracted (value={hit.value!r})")
    return hit


def parse_json_value(raw: str) -> Any:
    text = raw.strip()
    if not text or text == "—":
        raise AssertionError("empty JSON field value")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {raw!r}") from exc


def assert_is_json_list(raw: str, *, field_name: str = "field") -> list[Any]:
    parsed = parse_json_value(raw)
    if not isinstance(parsed, list):
        raise AssertionError(f"{field_name} must be a JSON array, got {type(parsed).__name__}: {raw!r}")
    return parsed


def assert_number_scalar(
    field: ExtractedFieldResult,
    expected: float,
    *,
    tolerance: float = 0.01,
    label: str | None = None,
) -> None:
    name = label or field.key
    parsed = parse_numeric_value(field.value)
    if parsed is None:
        raise AssertionError(f"{name}: could not parse number from {field.value!r}")
    if abs(parsed - expected) > tolerance:
        raise AssertionError(f"{name}: {parsed} != {expected} (±{tolerance})")


def assert_integer_scalar(
    field: ExtractedFieldResult,
    expected: int,
    *,
    label: str | None = None,
) -> None:
    name = label or field.key
    parsed = parse_numeric_value(field.value)
    if parsed is None or int(parsed) != expected:
        raise AssertionError(f"{name}: expected integer {expected}, got {field.value!r}")


def assert_verbatim_contains(field: ExtractedFieldResult, *needles: str) -> None:
    upper = field.value.upper()
    for needle in needles:
        if needle.upper() not in upper:
            raise AssertionError(f"{field.key}: expected {needle!r} in {field.value!r}")


def assert_date_scalar(field: ExtractedFieldResult, expected_iso: str) -> None:
    value = field.value.strip()
    if is_iso_date_like(value):
        if value != expected_iso:
            raise AssertionError(f"{field.key}: {value} != {expected_iso}")
        return
    if _DATE_DD_MM_YYYY.match(value):
        parts = value.split("/")
        iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
        if iso != expected_iso:
            raise AssertionError(f"{field.key}: {value} -> {iso} != {expected_iso}")
        return
    raise AssertionError(f"{field.key}: not a date: {value!r}")


def assert_currency_scalar(field: ExtractedFieldResult, *accepted: str) -> None:
    upper = field.value.upper()
    if not any(token.upper() in upper for token in accepted):
        raise AssertionError(f"{field.key}: expected one of {accepted}, got {field.value!r}")


def assert_enum_scalar(field: ExtractedFieldResult, allowed: set[str]) -> None:
    token = field.value.strip().upper()
    normalized = {item.upper() for item in allowed}
    if token not in normalized:
        raise AssertionError(f"{field.key}: {field.value!r} not in {sorted(allowed)}")


def assert_multi_enum(field: ExtractedFieldResult, required: set[str]) -> None:
    items = assert_is_json_list(field.value, field_name=field.key)
    found = {str(item).strip().upper() for item in items}
    missing = {item.upper() for item in required if item.upper() not in found}
    if missing:
        raise AssertionError(f"{field.key}: missing categories {sorted(missing)} in {found}")


def assert_number_list(
    field: ExtractedFieldResult,
    *,
    expected_len: int,
    expected_sum: float,
    sum_tolerance: float = 0.5,
    len_tolerance: int = 0,
) -> list[float]:
    items = assert_is_json_list(field.value, field_name=field.key)
    if len_tolerance == 0:
        if len(items) != expected_len:
            raise AssertionError(f"{field.key}: expected {expected_len} items, got {len(items)}")
    elif abs(len(items) - expected_len) > len_tolerance:
        raise AssertionError(
            f"{field.key}: expected ~{expected_len} items (±{len_tolerance}), got {len(items)}"
        )
    amounts: list[float] = []
    for index, item in enumerate(items):
        parsed = parse_numeric_value(str(item))
        if parsed is None:
            raise AssertionError(f"{field.key}[{index}]: not numeric: {item!r}")
        amounts.append(parsed)
    total = round(sum(amounts), 2)
    if abs(total - expected_sum) > sum_tolerance:
        raise AssertionError(
            f"{field.key}: sum {total} != {expected_sum} (±{sum_tolerance})"
        )
    return amounts


def assert_date_list(
    field: ExtractedFieldResult,
    *,
    expected_len: int,
    len_tolerance: int = 0,
) -> list[str]:
    items = assert_is_json_list(field.value, field_name=field.key)
    if len_tolerance == 0:
        if len(items) != expected_len:
            raise AssertionError(f"{field.key}: expected {expected_len} dates, got {len(items)}")
    elif abs(len(items) - expected_len) > len_tolerance:
        raise AssertionError(
            f"{field.key}: expected ~{expected_len} dates (±{len_tolerance}), got {len(items)}"
        )
    normalized: list[str] = []
    for index, item in enumerate(items):
        token = str(item).strip()
        if is_iso_date_like(token):
            normalized.append(token)
            continue
        if _DATE_DD_MM.match(token):
            normalized.append(token)
            continue
        if _DATE_DD_MM_YYYY.match(token):
            day, month, year = token.split("/")
            normalized.append(f"{year}-{month}-{day}")
            continue
        raise AssertionError(f"{field.key}[{index}]: invalid date {token!r}")
    return normalized


def assert_verbatim_string_list(
    field: ExtractedFieldResult,
    *,
    expected_len: int,
    must_include: tuple[str, ...] = (),
    len_tolerance: int = 0,
) -> list[str]:
    items = assert_is_json_list(field.value, field_name=field.key)
    if len_tolerance == 0:
        if len(items) != expected_len:
            raise AssertionError(f"{field.key}: expected {expected_len} strings, got {len(items)}")
    elif abs(len(items) - expected_len) > len_tolerance:
        raise AssertionError(
            f"{field.key}: expected ~{expected_len} strings (±{len_tolerance}), got {len(items)}"
        )
    strings = [str(item).strip() for item in items]
    joined = " ".join(strings).upper()
    for needle in must_include:
        if needle.upper() not in joined:
            raise AssertionError(f"{field.key}: missing expected label {needle!r}")
    return strings


def assert_object_array_transactions(
    field: ExtractedFieldResult,
    gt: CihReleveGroundTruth,
    *,
    row_tolerance: int = 0,
    sum_tolerance: float = 1.0,
) -> list[dict[str, Any]]:
    rows = assert_is_json_list(field.value, field_name=field.key)
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise AssertionError(f"{field.key}: expected list of objects")
    expected_rows = len(gt.transactions)
    if row_tolerance == 0:
        if len(rows) != expected_rows:
            raise AssertionError(f"{field.key}: expected {expected_rows} rows, got {len(rows)}")
    elif abs(len(rows) - expected_rows) > row_tolerance:
        raise AssertionError(
            f"{field.key}: expected ~{expected_rows} rows (±{row_tolerance}), got {len(rows)}"
        )

    debit_total = 0.0
    credit_total = 0.0
    debit_rows = 0
    credit_rows = 0
    for index, row in enumerate(rows):
        debit_raw = row.get("debit_amount")
        credit_raw = row.get("credit_amount")
        description = str(row.get("description") or "").strip()
        op_date = str(row.get("operation_date") or row.get("value_date") or "").strip()
        if not description:
            raise AssertionError(f"{field.key}[{index}]: missing description")
        if not op_date:
            raise AssertionError(f"{field.key}[{index}]: missing operation_date")
        if debit_raw not in (None, "", "—", "null"):
            debit = parse_numeric_value(str(debit_raw))
            if debit is None:
                raise AssertionError(f"{field.key}[{index}].debit_amount not numeric: {debit_raw!r}")
            debit_total += debit
            debit_rows += 1
        if credit_raw not in (None, "", "—", "null"):
            credit = parse_numeric_value(str(credit_raw))
            if credit is None:
                raise AssertionError(f"{field.key}[{index}].credit_amount not numeric: {credit_raw!r}")
            credit_total += credit
            credit_rows += 1

    debit_total = round(debit_total, 2)
    credit_total = round(credit_total, 2)
    if row_tolerance == 0:
        if debit_rows != gt.debit_count:
            raise AssertionError(f"{field.key}: expected {gt.debit_count} debit rows, got {debit_rows}")
        if credit_rows != gt.credit_count:
            raise AssertionError(f"{field.key}: expected {gt.credit_count} credit rows, got {credit_rows}")
    if abs(debit_total - gt.total_debit_movements) > sum_tolerance:
        raise AssertionError(
            f"{field.key}: debit total {debit_total} != {gt.total_debit_movements}"
        )
    if abs(credit_total - gt.total_credit_movements) > sum_tolerance:
        raise AssertionError(
            f"{field.key}: credit total {credit_total} != {gt.total_credit_movements}"
        )
    return rows


def assert_balance_identity(
    opening: float,
    closing: float,
    total_debits: float,
    total_credits: float,
    *,
    tolerance: float = 0.05,
) -> None:
    expected = round(opening + total_credits - total_debits, 2)
    if abs(expected - closing) > tolerance:
        raise AssertionError(
            f"balance identity failed: {opening} + {total_credits} - {total_debits} "
            f"= {expected}, closing={closing}"
        )


def assert_opening_date_in_list(dates: list[str], opening_iso: str) -> None:
    """Opening balance date may appear only in header, not in movement list."""
    _ = opening_iso
    for token in dates:
        if is_iso_date_like(token):
            datetime.fromisoformat(token)
        elif _DATE_DD_MM.match(token):
            continue
        elif _DATE_DD_MM_YYYY.match(token):
            continue
        else:
            raise AssertionError(f"unexpected date token in list: {token!r}")


def assert_list_not_scalar(field: ExtractedFieldResult) -> None:
    parsed = parse_json_value(field.value)
    if not isinstance(parsed, list):
        raise AssertionError(f"{field.key} must be JSON array, got {type(parsed).__name__}")


def assert_normalized_amount(field: ExtractedFieldResult, locale_form: str) -> None:
    if normalize_amount(field.value) != normalize_amount(locale_form):
        raise AssertionError(f"{field.key}: {field.value!r} != normalized {locale_form!r}")
