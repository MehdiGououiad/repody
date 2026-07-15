from audit_workbench.extraction.template_type_inference import suggest_template_type


def test_suggest_template_type_date_not_datetime():
    assert suggest_template_type("invoice_date", "Date on the invoice") == "date"


def test_suggest_template_type_email():
    assert suggest_template_type("contact_email", "") == "email-address"


def test_suggest_template_type_amount_is_number():
    assert suggest_template_type("total_amount", "Total TTC") == "number"
