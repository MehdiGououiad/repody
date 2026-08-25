from repody.extraction.nuextract import (
    DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
    resolve_template_type,
    suggest_template_type,
)


def test_suggest_template_type_is_document_agnostic_default():
    assert (
        suggest_template_type("invoice_date", "Date on the invoice")
        == DEFAULT_NUEXTRACT_TEMPLATE_TYPE
    )
    assert suggest_template_type("contact_email", "") == DEFAULT_NUEXTRACT_TEMPLATE_TYPE
    assert suggest_template_type("total_amount", "Total TTC") == DEFAULT_NUEXTRACT_TEMPLATE_TYPE
    assert suggest_template_type("custom_label", "") == DEFAULT_NUEXTRACT_TEMPLATE_TYPE


def test_resolve_template_type_uses_explicit_only():
    assert resolve_template_type("total", "amount", "number") == "number"
    assert resolve_template_type("total", "amount", None) == DEFAULT_NUEXTRACT_TEMPLATE_TYPE
