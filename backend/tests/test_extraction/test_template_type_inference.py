from audit_workbench.extraction.template_type_inference import (
    suggest_template_type,
    vlm_max_tokens_for_field_count,
)


def test_suggest_template_type_date_not_datetime():
    assert suggest_template_type("invoice_date", "Date on the invoice") == "date"


def test_suggest_template_type_email():
    assert suggest_template_type("contact_email", "") == "email-address"


def test_suggest_template_type_amount_is_number():
    assert suggest_template_type("total_amount", "Total TTC") == "number"


def test_vlm_max_tokens_scales_with_fields():
    assert vlm_max_tokens_for_field_count(0) == 128
    assert vlm_max_tokens_for_field_count(10) == 128 + 480
    assert vlm_max_tokens_for_field_count(100) == 4096
