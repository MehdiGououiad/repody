"""Ground truth for the CIH bank statement fixture (releve cih.pdf).

Values are derived from PDF text extraction (PyMuPDF), cross-checked against
statement footer totals (TOTAL DES MOUVEMENTS / NOUVEAU SOLDE).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import fitz

from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.field_json import parse_numeric_value

REPO_ROOT = Path(__file__).resolve().parents[3]
CIH_RELEVE_PDF = REPO_ROOT / "e2e" / "fixtures" / "documents" / "releve cih.pdf"

_TRANSACTION_LINE = re.compile(
    r"^\s*(\d{2}/\d{2})(\d{2}/\d{2})\s+(.+?)\s+([\d][\d\s]*,\d{2})\s*$",
    re.MULTILINE,
)
_OPENING_BALANCE = re.compile(
    r"SOLDE DEPART AU\s*:\s*(\d{2}/\d{2}/\d{4})\s+([\d\s]+,\d{2})",
)
_CLOSING_BALANCE = re.compile(
    r"NOUVEAU SOLDE AU\s+(\d{2}/\d{2}/\d{4})\s+([\d\s]+,\d{2})",
)
_FOOTER_TOTALS = re.compile(
    r"TOTAL DES MOUVEMENTS\s+([\d\s]+,\d{2})\s+([\d\s]+,\d{2})",
)
_ACCOUNT_NUMBER = re.compile(r"\b(\d{3})\s+(\d{3})\s+(\d{16})\s+(\d{2})\b")
_STATEMENT_YEAR = 2022


@dataclass(frozen=True)
class CihTransaction:
    operation_date: str
    value_date: str
    description: str
    amount: float
    is_credit: bool


@dataclass(frozen=True)
class CihReleveGroundTruth:
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
    transactions: tuple[CihTransaction, ...]

    @property
    def opening_balance_iso(self) -> str:
        day, month, year = self.opening_balance_date.split("/")
        return f"{year}-{month}-{day}"

    @property
    def closing_balance_iso(self) -> str:
        day, month, year = self.closing_balance_date.split("/")
        return f"{year}-{month}-{day}"

    @property
    def debit_amounts(self) -> tuple[float, ...]:
        return tuple(t.amount for t in self.transactions if not t.is_credit)

    @property
    def credit_amounts(self) -> tuple[float, ...]:
        return tuple(t.amount for t in self.transactions if t.is_credit)

    @property
    def operation_dates_iso(self) -> tuple[str, ...]:
        return tuple(_operation_iso(t.operation_date) for t in self.transactions)

    @property
    def value_dates_iso(self) -> tuple[str, ...]:
        return tuple(_operation_iso(t.value_date) for t in self.transactions)

    @property
    def transaction_descriptions(self) -> tuple[str, ...]:
        return tuple(t.description for t in self.transactions)

    @property
    def movement_categories(self) -> tuple[str, ...]:
        return tuple(_movement_category(t.description) for t in self.transactions)


def cih_releve_pdf_path() -> Path:
    return CIH_RELEVE_PDF


def load_cih_releve_bytes() -> bytes:
    path = cih_releve_pdf_path()
    if not path.is_file():
        raise FileNotFoundError(f"CIH fixture missing: {path}")
    return path.read_bytes()


def _operation_iso(dd_mm: str, *, year: int = _STATEMENT_YEAR) -> str:
    day, month = dd_mm.split("/")
    return f"{year}-{month}-{day}"


def _movement_category(description: str) -> str:
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


def load_cih_releve_text() -> str:
    doc = fitz.open(cih_releve_pdf_path())
    try:
        return "\n".join(doc[i].get_text("text") for i in range(doc.page_count))
    finally:
        doc.close()


def parse_cih_releve_ground_truth(text: str) -> CihReleveGroundTruth:
    opening = _OPENING_BALANCE.search(text)
    closing = _CLOSING_BALANCE.search(text)
    footer = _FOOTER_TOTALS.search(text)
    if not opening or not closing or not footer:
        raise ValueError("CIH relevé PDF text missing expected balance markers")

    transactions: list[CihTransaction] = []
    for match in _TRANSACTION_LINE.finditer(text):
        op_date, val_date, description, amount_raw = match.groups()
        amount = parse_numeric_value(amount_raw)
        if amount is None:
            continue
        desc = description.strip()
        is_credit = desc.startswith("VERSEMENT DE")
        transactions.append(
            CihTransaction(
                operation_date=op_date,
                value_date=val_date,
                description=desc,
                amount=amount,
                is_credit=is_credit,
            )
        )

    debits = [t for t in transactions if not t.is_credit]
    credits = [t for t in transactions if t.is_credit]
    debit_sum = round(sum(t.amount for t in debits), 2)
    credit_sum = round(sum(t.amount for t in credits), 2)
    footer_debits = parse_numeric_value(footer.group(1))
    footer_credits = parse_numeric_value(footer.group(2))
    if footer_debits is None or footer_credits is None:
        raise ValueError("Could not parse CIH footer totals")
    if debit_sum != footer_debits or credit_sum != footer_credits:
        raise ValueError(
            f"Parsed movements {debit_sum}/{credit_sum} != footer {footer_debits}/{footer_credits}"
        )

    opening_balance = parse_numeric_value(opening.group(2))
    closing_balance = parse_numeric_value(closing.group(2))
    if opening_balance is None or closing_balance is None:
        raise ValueError("Could not parse opening/closing balances")

    expected_close = round(opening_balance + credit_sum - debit_sum, 2)
    if abs(expected_close - closing_balance) > 0.02:
        raise ValueError(
            f"Balance identity failed: {opening_balance} + {credit_sum} - {debit_sum} "
            f"= {expected_close}, expected {closing_balance}"
        )

    holder_match = re.search(r"JARROUMI\s+SAFAA", text)
    if not holder_match:
        raise ValueError("Account holder JARROUMI SAFAA not found in fixture text")

    account_match = _ACCOUNT_NUMBER.search(text)
    if not account_match:
        raise ValueError("Account number line not found in fixture text")
    account_number = account_match.group(3)

    page_markers = re.findall(r"\b00[12]/2\b", text)
    page_count = max(2, len(set(page_markers)) or 2)

    return CihReleveGroundTruth(
        page_count=page_count,
        account_holder="JARROUMI SAFAA",
        account_number=account_number,
        agency="SIDI BENNOUR",
        currency="MAD",
        opening_balance_date=opening.group(1),
        opening_balance=opening_balance,
        closing_balance_date=closing.group(1),
        closing_balance=closing_balance,
        total_debit_movements=footer_debits,
        total_credit_movements=footer_credits,
        debit_count=len(debits),
        credit_count=len(credits),
        transactions=tuple(transactions),
    )


@lru_cache
def get_cih_releve_ground_truth() -> CihReleveGroundTruth:
    return parse_cih_releve_ground_truth(load_cih_releve_text())


def cih_summary_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="account_holder",
            description="Account holder full name as printed on the statement header",
            template_type="verbatim-string",
        ),
        SchemaFieldSpec(
            name="account_number",
            description="N° DE COMPTE — 20 digit account number",
            template_type="string",
        ),
        SchemaFieldSpec(
            name="agency",
            description="Branch / agence name",
            template_type="verbatim-string",
        ),
        SchemaFieldSpec(
            name="currency",
            description="Account currency (DEVISE)",
            template_type="currency",
        ),
        SchemaFieldSpec(
            name="opening_balance_date",
            description="SOLDE DEPART date",
            template_type="date",
        ),
        SchemaFieldSpec(
            name="closing_balance_date",
            description="NOUVEAU SOLDE date",
            template_type="date",
        ),
        SchemaFieldSpec(
            name="opening_balance",
            description="SOLDE DEPART opening balance amount",
            template_type="number",
        ),
        SchemaFieldSpec(
            name="closing_balance",
            description="NOUVEAU SOLDE closing balance amount",
            template_type="number",
        ),
        SchemaFieldSpec(
            name="total_debit_movements",
            description="TOTAL DES MOUVEMENTS debit column total for the period",
            template_type="number",
        ),
        SchemaFieldSpec(
            name="total_credit_movements",
            description="TOTAL DES MOUVEMENTS credit column total for the period",
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


def cih_debit_list_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="transaction_debit_amounts",
            description="Every debit movement amount on the statement, one per row, in order",
            template_type="number-list",
        ),
    ]


def cih_list_fields_schema() -> list[SchemaFieldSpec]:
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
            description="Operation date for each movement row, same order as the statement table",
            template_type="date-list",
        ),
        SchemaFieldSpec(
            name="transaction_descriptions",
            description="Libellé / description for each movement row in statement order",
            template_type="verbatim-string-list",
        ),
        SchemaFieldSpec(
            name="movement_categories",
            description="Distinct movement categories present on the statement",
            template_type="multi-enum",
            enum_values=["DEPOSIT", "TRANSFER", "WITHDRAWAL", "CARD", "FEE", "OTHER"],
        ),
    ]


def cih_transactions_schema() -> list[SchemaFieldSpec]:
    return [
        SchemaFieldSpec(
            name="transactions",
            description="All account movements in statement order",
            template_type="object-array",
            children=[
                SchemaFieldSpec(
                    name="operation_date",
                    description="Operation date from DATES OPER column (ISO date)",
                    template_type="date",
                ),
                SchemaFieldSpec(
                    name="value_date",
                    description="Value date from VALEUR column (ISO date)",
                    template_type="date",
                ),
                SchemaFieldSpec(
                    name="description",
                    description="Operation label / libellé",
                    template_type="verbatim-string",
                ),
                SchemaFieldSpec(
                    name="category",
                    description="Movement category",
                    template_type="enum",
                    enum_values=["DEPOSIT", "TRANSFER", "WITHDRAWAL", "CARD", "FEE", "OTHER"],
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


def cih_full_schema() -> list[SchemaFieldSpec]:
    """Combined scalar + list + enum + object-array schema for end-to-end extraction."""
    combined: list[SchemaFieldSpec] = []
    seen: set[str] = set()
    for block in (
        cih_summary_schema(),
        cih_list_fields_schema(),
        cih_transactions_schema(),
    ):
        for field in block:
            if field.name in seen:
                continue
            seen.add(field.name)
            combined.append(field)
    return combined


def all_cih_schema_fields() -> dict[str, SchemaFieldSpec]:
    registry: dict[str, SchemaFieldSpec] = {}
    for field in cih_full_schema():
        registry[field.name] = field
    return registry


def build_cih_model_payload(schema: list[SchemaFieldSpec]) -> dict[str, Any]:
    """NuExtract-shaped JSON object for mocked / golden responses."""
    gt = get_cih_releve_ground_truth()
    payload: dict[str, Any] = {}
    for field in schema:
        name = field.name.strip()
        template_type = (field.template_type or "").strip()
        if name == "account_holder":
            payload[name] = gt.account_holder
        elif name == "account_number":
            payload[name] = gt.account_number
        elif name == "agency":
            payload[name] = gt.agency
        elif name == "currency":
            payload[name] = "MAD"
        elif name == "currency_code":
            payload[name] = "MAD"
        elif name == "opening_balance_date":
            payload[name] = gt.opening_balance_iso
        elif name == "closing_balance_date":
            payload[name] = gt.closing_balance_iso
        elif name == "opening_balance":
            payload[name] = gt.opening_balance
        elif name == "closing_balance":
            payload[name] = gt.closing_balance
        elif name == "total_debit_movements":
            payload[name] = gt.total_debit_movements
        elif name == "total_credit_movements":
            payload[name] = gt.total_credit_movements
        elif name == "debit_transaction_count":
            payload[name] = gt.debit_count
        elif name == "credit_transaction_count":
            payload[name] = gt.credit_count
        elif name == "transaction_debit_amounts" and template_type == "number-list":
            payload[name] = list(gt.debit_amounts)
        elif name == "transaction_credit_amounts" and template_type == "number-list":
            payload[name] = list(gt.credit_amounts)
        elif name == "operation_dates" and template_type == "date-list":
            payload[name] = list(gt.operation_dates_iso)
        elif name == "transaction_descriptions" and template_type == "verbatim-string-list":
            payload[name] = list(gt.transaction_descriptions)
        elif name == "movement_categories" and template_type == "multi-enum":
            payload[name] = sorted(set(gt.movement_categories))
        elif name == "transactions" and template_type == "object-array":
            payload[name] = [
                {
                    "operation_date": _operation_iso(t.operation_date),
                    "value_date": _operation_iso(t.value_date),
                    "description": t.description,
                    "category": _movement_category(t.description),
                    "debit_amount": None if t.is_credit else t.amount,
                    "credit_amount": t.amount if t.is_credit else None,
                }
                for t in gt.transactions
            ]
        else:
            payload[name] = None
    return payload
