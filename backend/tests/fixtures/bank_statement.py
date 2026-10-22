"""Ground truth and schemas for the synthetic bank statement (bank-statement.pdf).

Values are parsed back from the PDF text and cross-checked against the footer totals,
so a regenerated fixture that drifts from its own totals fails loudly.
Regenerate with ``python scripts/generate_bank_statement_fixture.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pymupdf

from repody.extraction.types import SchemaFieldSpec
from repody.rules.amounts import parse_numeric_value

BANK_STATEMENT_PDF = (
    Path(__file__).resolve().parents[3] / "e2e" / "fixtures" / "documents" / "bank-statement.pdf"
)
STATEMENT_YEAR = 2025
CATEGORIES = ["DEPOSIT", "TRANSFER", "WITHDRAWAL", "CARD", "FEE", "OTHER"]

_MOVEMENT = re.compile(
    r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s{2,}(\d[\d ]*,\d{2})\s*$",
    re.MULTILINE,
)
_OPENING = re.compile(r"SOLDE DEPART AU\s*:\s*(\d{2}/\d{2}/\d{4})\s+(\d[\d ]*,\d{2})")
_CLOSING = re.compile(r"NOUVEAU SOLDE AU\s*:\s*(\d{2}/\d{2}/\d{4})\s+(\d[\d ]*,\d{2})")
_FOOTER = re.compile(r"TOTAL DES MOUVEMENTS\s+(\d[\d ]*,\d{2})\s+(\d[\d ]*,\d{2})")
_HOLDER = re.compile(r"TITULAIRE\s*:\s*(.+)")
_AGENCY = re.compile(r"AGENCE\s*:\s*(.+)")
_ACCOUNT = re.compile(r"NUMERO DE COMPTE\s*:\s*\d{3} \d{3} (\d{16}) \d{2}")


@dataclass(frozen=True)
class Movement:
    operation_date: str
    value_date: str
    description: str
    amount: float
    is_credit: bool


@dataclass(frozen=True)
class StatementGroundTruth:
    page_count: int
    account_holder: str
    account_number: str
    agency: str
    currency: str
    opening_balance_date: str
    opening_balance: float
    closing_balance_date: str
    closing_balance: float
    total_debit_movements: float
    total_credit_movements: float
    debit_count: int
    credit_count: int
    movements: tuple[Movement, ...]

    @property
    def opening_balance_iso(self) -> str:
        return _iso(self.opening_balance_date)

    @property
    def closing_balance_iso(self) -> str:
        return _iso(self.closing_balance_date)

    @property
    def debit_amounts(self) -> tuple[float, ...]:
        return tuple(m.amount for m in self.movements if not m.is_credit)

    @property
    def credit_amounts(self) -> tuple[float, ...]:
        return tuple(m.amount for m in self.movements if m.is_credit)

    @property
    def operation_dates_iso(self) -> tuple[str, ...]:
        return tuple(_iso(f"{m.operation_date}/{STATEMENT_YEAR}") for m in self.movements)

    @property
    def descriptions(self) -> tuple[str, ...]:
        return tuple(m.description for m in self.movements)

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(movement_category(m.description) for m in self.movements)


def _iso(dd_mm_yyyy: str) -> str:
    day, month, year = dd_mm_yyyy.split("/")
    return f"{year}-{month}-{day}"


def movement_category(description: str) -> str:
    upper = description.upper()
    if upper.startswith("VERSEMENT"):
        return "DEPOSIT"
    if "VIREMENT EMIS" in upper:
        return "TRANSFER"
    if "RETRAIT" in upper:
        return "WITHDRAWAL"
    if "FRAIS" in upper or "DROIT DE TIMBRE" in upper:
        return "FEE"
    if "PAIEMENT" in upper or "RECHARGE" in upper:
        return "CARD"
    return "OTHER"


def load_bank_statement_bytes() -> bytes:
    return BANK_STATEMENT_PDF.read_bytes()


def load_bank_statement_text() -> tuple[str, int]:
    doc = pymupdf.open(BANK_STATEMENT_PDF)
    try:
        return "\n".join(page.get_text("text") for page in doc), doc.page_count
    finally:
        doc.close()


def _amount(raw: str) -> float:
    value = parse_numeric_value(raw)
    if value is None:
        raise ValueError(f"not an amount: {raw!r}")
    return value


def _search(pattern: re.Pattern[str], text: str) -> re.Match[str]:
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"bank statement text has no match for {pattern.pattern!r}")
    return match


def parse_bank_statement(text: str, page_count: int) -> StatementGroundTruth:
    movements = tuple(
        Movement(
            operation_date=op,
            value_date=val,
            description=desc.strip(),
            amount=_amount(raw),
            is_credit=desc.strip().startswith("VERSEMENT"),
        )
        for op, val, desc, raw in _MOVEMENT.findall(text)
    )
    debits = [m for m in movements if not m.is_credit]
    credits = [m for m in movements if m.is_credit]

    footer = _search(_FOOTER, text)
    total_debits, total_credits = _amount(footer.group(1)), _amount(footer.group(2))
    if round(sum(m.amount for m in debits), 2) != total_debits:
        raise ValueError("debit rows do not add up to the footer total")
    if round(sum(m.amount for m in credits), 2) != total_credits:
        raise ValueError("credit rows do not add up to the footer total")

    opening = _search(_OPENING, text)
    closing = _search(_CLOSING, text)
    opening_balance, closing_balance = _amount(opening.group(2)), _amount(closing.group(2))
    if round(opening_balance + total_credits - total_debits, 2) != closing_balance:
        raise ValueError("opening + credits - debits does not equal the closing balance")

    return StatementGroundTruth(
        page_count=page_count,
        account_holder=_search(_HOLDER, text).group(1).strip(),
        account_number=_search(_ACCOUNT, text).group(1),
        agency=_search(_AGENCY, text).group(1).strip(),
        currency="MAD",
        opening_balance_date=opening.group(1),
        opening_balance=opening_balance,
        closing_balance_date=closing.group(1),
        closing_balance=closing_balance,
        total_debit_movements=total_debits,
        total_credit_movements=total_credits,
        debit_count=len(debits),
        credit_count=len(credits),
        movements=movements,
    )


@lru_cache
def get_bank_statement_ground_truth() -> StatementGroundTruth:
    return parse_bank_statement(*load_bank_statement_text())


def summary_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="account_holder",
            description="Account holder full name as printed on the statement header",
            template_type="verbatim-string",
        ),
        SchemaFieldSpec(
            name="account_number",
            description="16-digit account number between the bank and key segments",
            template_type="string",
        ),
        SchemaFieldSpec(name="agency", description="Branch name", template_type="verbatim-string"),
        SchemaFieldSpec(name="currency", description="Account currency", template_type="currency"),
        SchemaFieldSpec(
            name="opening_balance_date", description="SOLDE DEPART date", template_type="date"
        ),
        SchemaFieldSpec(
            name="closing_balance_date", description="NOUVEAU SOLDE date", template_type="date"
        ),
        SchemaFieldSpec(
            name="opening_balance", description="Opening balance amount", template_type="number"
        ),
        SchemaFieldSpec(
            name="closing_balance", description="Closing balance amount", template_type="number"
        ),
        SchemaFieldSpec(
            name="total_debit_movements",
            description="TOTAL DES MOUVEMENTS debit column total",
            template_type="number",
        ),
        SchemaFieldSpec(
            name="total_credit_movements",
            description="TOTAL DES MOUVEMENTS credit column total",
            template_type="number",
        ),
        SchemaFieldSpec(
            name="debit_transaction_count",
            description="Count of debit movement lines",
            template_type="integer",
        ),
        SchemaFieldSpec(
            name="credit_transaction_count",
            description="Count of credit movement lines",
            template_type="integer",
        ),
        SchemaFieldSpec(
            name="currency_code",
            description="ISO currency code for the account",
            template_type="enum",
            enum_values=["MAD", "EUR", "USD"],
        ),
    ]


def debit_list_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="transaction_debit_amounts",
            description="Every debit movement amount on the statement, one per row, in order",
            template_type="number-list",
        ),
    ]


def list_fields_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="transaction_debit_amounts",
            description="Every debit amount, one list element per debit line in order",
            template_type="number-list",
        ),
        SchemaFieldSpec(
            name="transaction_credit_amounts",
            description="Every credit amount, one list element per credit line in order",
            template_type="number-list",
        ),
        SchemaFieldSpec(
            name="operation_dates",
            description="Operation date for each movement row, in statement order",
            template_type="date-list",
        ),
        SchemaFieldSpec(
            name="transaction_descriptions",
            description="Description (LIBELLE) for each movement row, in statement order",
            template_type="verbatim-string-list",
        ),
        SchemaFieldSpec(
            name="movement_categories",
            description="Distinct movement categories present on the statement",
            template_type="multi-enum",
            enum_values=CATEGORIES,
        ),
    ]


def transactions_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="transactions",
            description="All account movements in statement order",
            template_type="object-array",
            children=[
                SchemaFieldSpec(
                    name="operation_date", description="OPER column date", template_type="date"
                ),
                SchemaFieldSpec(
                    name="value_date", description="VALEUR column date", template_type="date"
                ),
                SchemaFieldSpec(
                    name="description",
                    description="LIBELLE column text",
                    template_type="verbatim-string",
                ),
                SchemaFieldSpec(
                    name="category",
                    description="Movement category",
                    template_type="enum",
                    enum_values=CATEGORIES,
                ),
                SchemaFieldSpec(
                    name="debit_amount",
                    description="Debit amount when present, otherwise null",
                    template_type="number",
                ),
                SchemaFieldSpec(
                    name="credit_amount",
                    description="Credit amount when present, otherwise null",
                    template_type="number",
                ),
            ],
        ),
    ]


def full_schema() -> list[SchemaFieldSpec]:
    combined: dict[str, SchemaFieldSpec] = {}
    for block in (summary_schema(), list_fields_schema(), transactions_schema()):
        for field in block:
            combined.setdefault(field.name, field)
    return list(combined.values())


def model_payload(schema: list[SchemaFieldSpec]) -> dict[str, Any]:
    """NuExtract-shaped answer a perfect model would return for ``schema``."""
    gt = get_bank_statement_ground_truth()
    answers: dict[str, Any] = {
        "account_holder": gt.account_holder,
        "account_number": gt.account_number,
        "agency": gt.agency,
        "currency": gt.currency,
        "currency_code": gt.currency,
        "opening_balance_date": gt.opening_balance_iso,
        "closing_balance_date": gt.closing_balance_iso,
        "opening_balance": gt.opening_balance,
        "closing_balance": gt.closing_balance,
        "total_debit_movements": gt.total_debit_movements,
        "total_credit_movements": gt.total_credit_movements,
        "debit_transaction_count": gt.debit_count,
        "credit_transaction_count": gt.credit_count,
        "transaction_debit_amounts": list(gt.debit_amounts),
        "transaction_credit_amounts": list(gt.credit_amounts),
        "operation_dates": list(gt.operation_dates_iso),
        "transaction_descriptions": list(gt.descriptions),
        "movement_categories": sorted(set(gt.categories)),
        "transactions": [
            {
                "operation_date": _iso(f"{m.operation_date}/{STATEMENT_YEAR}"),
                "value_date": _iso(f"{m.value_date}/{STATEMENT_YEAR}"),
                "description": m.description,
                "category": movement_category(m.description),
                "debit_amount": None if m.is_credit else m.amount,
                "credit_amount": m.amount if m.is_credit else None,
            }
            for m in gt.movements
        ],
    }
    return {field.name: answers.get(field.name) for field in schema}
