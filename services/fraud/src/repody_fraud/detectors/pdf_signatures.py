"""Tier-1 cryptographic PDF digital signature verification via ``pyHanko``."""

import io
from typing import Any

from pyhanko.pdf_utils.misc import PdfReadError
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.diff_analysis import DEFAULT_DIFF_POLICY
from pyhanko.sign.diff_analysis.policy_api import ModificationLevel
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

from repody_common.contracts import FraudFinding


def analyze_pdf_signatures(data: bytes) -> list[FraudFinding]:
    """Validate embedded PAdES / PDF signatures and post-sign incremental updates."""
    if not data.lstrip().startswith(b"%PDF-"):
        return []

    findings: list[FraudFinding] = []
    try:
        reader = PdfFileReader(io.BytesIO(data), strict=False)
        embedded = list(reader.embedded_signatures)
    except (PdfReadError, Exception) as exc:
        return [
            FraudFinding(
                detector="pdf_signatures",
                tier=1,
                code="PDF_SIG_UNREADABLE",
                severity="medium",
                title="Unable to inspect PDF signature objects",
                detail=f"pyHanko could not parse PDF signature structures: {exc}",
            )
        ]

    if not embedded:
        return findings

    vc = ValidationContext(allow_fetching=False)
    for sig_idx, sig in enumerate(embedded, start=1):
        field_name = sig.field_name or f"sig_{sig_idx}"
        try:
            status: Any = validate_pdf_signature(
                sig,
                signer_validation_context=vc,
                diff_policy=DEFAULT_DIFF_POLICY,
            )
        except Exception as exc:
            findings.append(
                FraudFinding(
                    detector="pdf_signatures",
                    tier=1,
                    code="PDF_SIG_INVALID",
                    severity="critical",
                    title="Corrupted PDF digital signature",
                    detail=f"Signature '{field_name}' failed validation: {exc}",
                )
            )
            continue

        if not bool(getattr(status, "intact", False)) or not bool(getattr(status, "valid", False)):
            findings.append(
                FraudFinding(
                    detector="pdf_signatures",
                    tier=1,
                    code="PDF_SIG_INVALID",
                    severity="critical",
                    title="Cryptographically invalid PDF digital signature",
                    detail=(
                        f"Signature '{field_name}' failed cryptographic integrity check "
                        f"({status.summary()})."
                    ),
                )
            )
            continue

        mod_level = getattr(status, "modification_level", None)
        docmdp_ok = getattr(status, "docmdp_ok", True)
        if mod_level == ModificationLevel.OTHER or docmdp_ok is False:
            findings.append(
                FraudFinding(
                    detector="pdf_signatures",
                    tier=1,
                    code="PDF_SIG_MODIFIED_AFTER_SIGNING",
                    severity="critical",
                    title="PDF modified after digital signature",
                    detail=(
                        f"Signature '{field_name}' covers an earlier revision, and unauthorized "
                        "changes were appended afterward."
                    ),
                )
            )
        elif not bool(getattr(status, "trusted", False)):
            findings.append(
                FraudFinding(
                    detector="pdf_signatures",
                    tier=1,
                    code="PDF_SIG_UNTRUSTED_CA",
                    severity="low",
                    title="PDF signed by unverified or self-signed certificate",
                    detail=(
                        f"Signature '{field_name}' is intact, but its CA root is not in the "
                        "configured on-prem trust store."
                    ),
                )
            )

    return findings
