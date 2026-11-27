"""Tier-2 post-extraction cross-field math, IBAN/BIC, ICAO 9303 MRZ, phone, and date logic."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import phonenumbers
import structlog
from schwifty import BIC, IBAN

from repody_common.contracts import FraudFinding

log = structlog.get_logger(__name__)

_MRZ_WEIGHTS = (7, 3, 1)
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y%m%d")


@dataclass(frozen=True, slots=True)
class _MrzGeometry:
    doc_number: str
    birth_yymmdd: str
    expiry_yymmdd: str
    checks: list[tuple[str, str, str]]


def _mrz_char_value(ch: str) -> int:
    if ch == "<":
        return 0
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    return 0


def compute_mrz_check_digit(value: str) -> str:
    """Compute an ICAO Doc 9303 Part 3 check digit using ``7, 3, 1`` weights mod 10."""
    total = sum(_mrz_char_value(ch) * _MRZ_WEIGHTS[i % 3] for i, ch in enumerate(value.upper()))
    return str(total % 10)


def _clean_mrz_lines(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(line).strip().upper().replace(" ", "") for line in raw if str(line).strip()]
    if isinstance(raw, str):
        return [line.strip().upper().replace(" ", "") for line in raw.splitlines() if line.strip()]
    return []


def _parse_mrz_geometry(lines: list[str]) -> _MrzGeometry | None:
    if len(lines) == 2 and len(lines[0]) >= 44 and len(lines[1]) >= 44:
        l2 = lines[1][:44]
        return _MrzGeometry(
            doc_number=l2[0:9],
            birth_yymmdd=l2[13:19],
            expiry_yymmdd=l2[21:27],
            checks=[
                ("document_number", l2[0:9], l2[9]),
                ("birth_date", l2[13:19], l2[19]),
                ("expiry_date", l2[21:27], l2[27]),
                ("personal_number", l2[28:42], l2[42]),
                ("composite", l2[0:10] + l2[13:20] + l2[21:43], l2[43]),
            ],
        )
    if len(lines) == 3 and all(len(line) >= 30 for line in lines):
        l1, l2 = lines[0][:30], lines[1][:30]
        return _MrzGeometry(
            doc_number=l1[5:14],
            birth_yymmdd=l2[0:6],
            expiry_yymmdd=l2[8:14],
            checks=[
                ("document_number", l1[5:14], l1[14]),
                ("birth_date", l2[0:6], l2[6]),
                ("expiry_date", l2[8:14], l2[14]),
                ("composite", l1[5:30] + l2[0:7] + l2[8:15] + l2[18:29], l2[29]),
            ],
        )
    if len(lines) == 2 and all(len(line) >= 36 for line in lines):
        l2 = lines[1][:36]
        return _MrzGeometry(
            doc_number=l2[0:9],
            birth_yymmdd=l2[13:19],
            expiry_yymmdd=l2[21:27],
            checks=[
                ("document_number", l2[0:9], l2[9]),
                ("birth_date", l2[13:19], l2[19]),
                ("expiry_date", l2[21:27], l2[27]),
                ("composite", l2[0:10] + l2[13:20] + l2[21:35], l2[35]),
            ],
        )
    return None


def _check_mrz_printed_fields(geom: _MrzGeometry, doc_fields: dict[str, Any]) -> list[FraudFinding]:
    findings: list[FraudFinding] = []
    printed_doc = (
        str(doc_fields.get("document_number") or doc_fields.get("passport_number") or "")
        .strip()
        .upper()
    )
    cleaned_mrz_doc = geom.doc_number.replace("<", "")
    if cleaned_mrz_doc and printed_doc and printed_doc.replace(" ", "") != cleaned_mrz_doc:
        findings.append(
            FraudFinding(
                detector="cross_field",
                tier=2,
                code="MRZ_PRINTED_FIELD_MISMATCH",
                severity="critical",
                title="Printed document number differs from MRZ",
                detail=f"Printed '{printed_doc}' != MRZ '{cleaned_mrz_doc}'.",
            )
        )

    for key, mrz_yymmdd in (("expiry_date", geom.expiry_yymmdd), ("birth_date", geom.birth_yymmdd)):
        parsed = _parse_date(doc_fields.get(key))
        if parsed and mrz_yymmdd.isdigit() and parsed.strftime("%y%m%d") != mrz_yymmdd:
            findings.append(
                FraudFinding(
                    detector="cross_field",
                    tier=2,
                    code="MRZ_PRINTED_FIELD_MISMATCH",
                    severity="critical",
                    title=f"Printed {key} differs from MRZ",
                    detail=f"Printed date '{parsed.isoformat()}' does not match MRZ '{mrz_yymmdd}'.",
                )
            )
    return findings


def _validate_mrz_lines(lines: list[str], doc_fields: dict[str, Any]) -> list[FraudFinding]:
    geom = _parse_mrz_geometry(lines)
    if geom is None:
        return [
            FraudFinding(
                detector="cross_field",
                tier=2,
                code="MRZ_FORMAT_INVALID",
                severity="high",
                title="Unrecognized ICAO 9303 MRZ geometry",
                detail=f"MRZ has {len(lines)} line(s) with lengths {[len(x) for x in lines]}.",
            )
        ]

    findings: list[FraudFinding] = []
    for label, segment, expected_digit in geom.checks:
        if expected_digit == "<" and set(segment) == {"<"}:
            continue
        actual_digit = compute_mrz_check_digit(segment)
        if actual_digit != expected_digit:
            findings.append(
                FraudFinding(
                    detector="cross_field",
                    tier=2,
                    code="MRZ_CHECK_DIGIT_FAILED",
                    severity="critical",
                    title="ICAO 9303 MRZ check digit mismatch",
                    detail=f"MRZ {label} check digit expected '{actual_digit}' but found '{expected_digit}'.",
                )
            )

    findings.extend(_check_mrz_printed_fields(geom, doc_fields))
    return findings


def _to_decimal(val: Any) -> Decimal | None:
    if isinstance(val, bool) or val is None:
        return None
    if isinstance(val, int | float | Decimal):
        return Decimal(str(val))
    if not isinstance(val, str):
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", val.strip())
    if not cleaned:
        return None
    cleaned = (
        cleaned.replace(",", ".")
        if ("," in cleaned and "." not in cleaned)
        else cleaned.replace(",", "")
    )
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(val: Any) -> date | None:
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if not isinstance(val, str):
        return None
    text = val.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC).date()
        except ValueError:
            continue
    return None


def _first_field(mapping: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    lowered = {k.lower(): v for k, v in mapping.items()}
    for name in candidates:
        if name in lowered and lowered[name] is not None:
            return lowered[name]
    return None


def _validate_single_phone(doc_name: str, key: str, val: str) -> FraudFinding | None:
    try:
        num = phonenumbers.parse(val.strip(), None)
        if phonenumbers.is_possible_number(num):
            return None
        return FraudFinding(
            detector="cross_field",
            tier=2,
            code="INVALID_PHONE",
            severity="low",
            title="Implausible international phone number",
            detail=f"[{doc_name}.{key}] '{val}' failed E.164 length validation.",
        )
    except phonenumbers.NumberParseException:
        return FraudFinding(
            detector="cross_field",
            tier=2,
            code="INVALID_PHONE",
            severity="low",
            title="Malformed international phone number",
            detail=f"[{doc_name}.{key}] could not parse '{val}'.",
        )


def _check_bank_and_phone(doc_name: str, fields: dict[str, Any]) -> list[FraudFinding]:
    findings: list[FraudFinding] = []
    parsed_iban: IBAN | None = None
    parsed_bic: BIC | None = None

    for key, val in fields.items():
        if not isinstance(val, str) or not val.strip():
            continue
        k_lower = key.lower()
        if "iban" in k_lower:
            try:
                parsed_iban = IBAN(val)
            except Exception as exc:
                findings.append(
                    FraudFinding(
                        detector="cross_field",
                        tier=2,
                        code="INVALID_IBAN",
                        severity="high",
                        title="Invalid IBAN checksum or structure",
                        detail=f"[{doc_name}.{key}] {exc}",
                    )
                )
        elif k_lower in ("bic", "swift", "swift_code", "bic_code"):
            try:
                parsed_bic = BIC(val)
            except Exception as exc:
                findings.append(
                    FraudFinding(
                        detector="cross_field",
                        tier=2,
                        code="INVALID_BIC",
                        severity="medium",
                        title="Invalid ISO 9362 BIC/SWIFT code",
                        detail=f"[{doc_name}.{key}] {exc}",
                    )
                )
        elif (
            any(tok in k_lower for tok in ("phone", "mobile", "tel"))
            and val.strip().startswith("+")
            and (phone_err := _validate_single_phone(doc_name, key, val))
        ):
            findings.append(phone_err)

    if (
        parsed_iban
        and parsed_bic
        and parsed_iban.bic
        and str(parsed_iban.bic)[:8] != str(parsed_bic)[:8]
    ):
        findings.append(
            FraudFinding(
                detector="cross_field",
                tier=2,
                code="IBAN_BIC_MISMATCH",
                severity="high",
                title="IBAN bank code conflicts with declared BIC",
                detail=f"[{doc_name}] IBAN maps to '{parsed_iban.bic}' != '{parsed_bic}'.",
            )
        )
    return findings


def _check_invoice_math(doc_name: str, fields: dict[str, Any]) -> list[FraudFinding]:
    findings: list[FraudFinding] = []
    subtotal = _to_decimal(_first_field(fields, ("subtotal", "amount_ht", "net_amount")))
    tax = _to_decimal(_first_field(fields, ("tax", "tva", "vat", "tax_amount", "vat_amount")))
    total = _to_decimal(
        _first_field(fields, ("total", "total_amount", "amount_ttc", "gross_amount"))
    )

    if (
        subtotal is not None
        and tax is not None
        and total is not None
        and abs((subtotal + tax) - total) > Decimal("0.02")
    ):
        findings.append(
            FraudFinding(
                detector="cross_field",
                tier=2,
                code="MATH_TOTAL_MISMATCH",
                severity="high",
                title="Invoice arithmetic discrepancy (subtotal + tax != total)",
                detail=f"[{doc_name}] {subtotal} + {tax} != {total}.",
            )
        )

    raw_items = _first_field(fields, ("line_items", "items", "lines"))
    target = subtotal if subtotal is not None else total
    if not isinstance(raw_items, list) or not raw_items or target is None:
        return findings

    item_amounts = [
        amt
        for item in raw_items
        if isinstance(item, dict)
        and (amt := _to_decimal(_first_field(item, ("total", "amount", "line_total")))) is not None
    ]
    if len(item_amounts) == len(raw_items):
        line_sum = sum(item_amounts, Decimal("0"))
        if abs(line_sum - target) > Decimal("0.05"):
            findings.append(
                FraudFinding(
                    detector="cross_field",
                    tier=2,
                    code="MATH_LINE_ITEMS_MISMATCH",
                    severity="high",
                    title="Line-item sum disagrees with invoice total/subtotal",
                    detail=f"[{doc_name}] sum(line_items)={line_sum} != {target}.",
                )
            )
    return findings


def _check_dates(doc_name: str, fields: dict[str, Any]) -> list[FraudFinding]:
    findings: list[FraudFinding] = []
    invoice_dt = _parse_date(_first_field(fields, ("invoice_date", "issue_date", "date")))
    due_dt = _parse_date(_first_field(fields, ("due_date",)))
    if invoice_dt and due_dt and due_dt < invoice_dt:
        findings.append(
            FraudFinding(
                detector="cross_field",
                tier=2,
                code="DATE_CHRONOLOGY_ERROR",
                severity="high",
                title="Due date precedes invoice issue date",
                detail=f"[{doc_name}] due_date ({due_dt}) < issue_date ({invoice_dt}).",
            )
        )

    birth_dt = _parse_date(_first_field(fields, ("birth_date", "date_of_birth", "dob")))
    expiry_dt = _parse_date(_first_field(fields, ("expiry_date", "expiration_date")))
    if birth_dt and expiry_dt and expiry_dt <= birth_dt:
        findings.append(
            FraudFinding(
                detector="cross_field",
                tier=2,
                code="ID_DATE_CHRONOLOGY_ERROR",
                severity="critical",
                title="ID expiry date is not after date of birth",
                detail=f"[{doc_name}] expiry_date ({expiry_dt}) <= birth_date ({birth_dt}).",
            )
        )
    return findings


def _check_document_fields(doc_name: str, fields: dict[str, Any]) -> list[FraudFinding]:
    findings: list[FraudFinding] = []
    findings.extend(_check_bank_and_phone(doc_name, fields))
    findings.extend(_check_invoice_math(doc_name, fields))
    findings.extend(_check_dates(doc_name, fields))

    mrz_lines = _clean_mrz_lines(
        _first_field(fields, ("mrz", "mrz_lines", "machine_readable_zone"))
    )
    if mrz_lines:
        findings.extend(_validate_mrz_lines(mrz_lines, fields))
    return findings


def analyze_cross_field_logic(extracted_data: dict[str, Any]) -> list[FraudFinding]:
    """Run Tier-2 deterministic math, IBAN/BIC, MRZ, phone, and date logic checks."""
    if not extracted_data:
        return []

    findings: list[FraudFinding] = []
    nested_docs = {k: v for k, v in extracted_data.items() if isinstance(v, dict)}
    if nested_docs:
        for doc_name, fields in nested_docs.items():
            findings.extend(_check_document_fields(doc_name, fields))
    else:
        findings.extend(_check_document_fields("document", extracted_data))
    return findings
