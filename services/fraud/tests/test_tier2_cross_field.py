"""Tier-2 cross-field logic tests: IBAN/BIC, ICAO 9303 MRZ, Decimal math, dates."""

from repody_fraud.detectors.cross_field import analyze_cross_field_logic, compute_mrz_check_digit


def _make_valid_td3_mrz() -> list[str]:
    doc_num = "12AB34567"
    dob = "900512"
    exp = "320512"
    opt = "<<<<<<<<<<<<<<"
    c_doc = compute_mrz_check_digit(doc_num)
    c_dob = compute_mrz_check_digit(dob)
    c_exp = compute_mrz_check_digit(exp)
    c_opt = compute_mrz_check_digit(opt)
    composite_src = f"{doc_num}{c_doc}{dob}{c_dob}{exp}{c_exp}{opt}{c_opt}"
    c_all = compute_mrz_check_digit(composite_src)
    line1 = "P<FRADUPONT<<ALICE<<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = f"{doc_num}{c_doc}FRA{dob}{c_dob}F{exp}{c_exp}{opt}{c_opt}{c_all}"
    return [line1, line2]


def test_valid_iban_bic_mrz_and_math_pass_cleanly() -> None:
    mrz = _make_valid_td3_mrz()
    data = {
        "Invoice": {
            "iban": "DE89370400440532013000",
            "bic": "COBADEFFXXX",
            "subtotal": "100.00",
            "tva": "20.00",
            "total": "120.00",
            "invoice_date": "2026-01-10",
            "due_date": "2026-02-10",
            "line_items": [{"total": "60.00"}, {"total": "40.00"}],
        },
        "Passport": {
            "document_number": "12AB34567",
            "birth_date": "1990-05-12",
            "expiry_date": "2032-05-12",
            "mrz_lines": mrz,
        },
    }
    assert analyze_cross_field_logic(data) == []


def test_corrupted_iban_bic_math_and_dates_are_flagged() -> None:
    data = {
        "Invoice": {
            "iban": "DE89370400440532013099",
            "bic": "NOTABIC",
            "subtotal": "100.00",
            "vat": "20.00",
            "total": "199.00",
            "invoice_date": "2026-05-10",
            "due_date": "2026-04-01",
            "phone": "+3312",
        }
    }
    codes = {f.code for f in analyze_cross_field_logic(data)}
    assert {
        "INVALID_IBAN",
        "INVALID_BIC",
        "MATH_TOTAL_MISMATCH",
        "DATE_CHRONOLOGY_ERROR",
        "INVALID_PHONE",
    }.issubset(codes)


def test_tampered_mrz_check_digit_and_printed_mismatch() -> None:
    mrz = _make_valid_td3_mrz()
    bad_line2 = mrz[1][:-1] + ("0" if mrz[1][-1] != "0" else "1")
    codes = {
        f.code
        for f in analyze_cross_field_logic(
            {
                "Passport": {
                    "document_number": "99ZZ00000",
                    "expiry_date": "2035-01-01",
                    "mrz_lines": [mrz[0], bad_line2],
                }
            }
        )
    }
    assert "MRZ_CHECK_DIGIT_FAILED" in codes
    assert "MRZ_PRINTED_FIELD_MISMATCH" in codes
