from audit_workbench.extraction.pdf_pages import pages_to_process


def test_pages_to_process_clamps_to_max():
    assert pages_to_process(20, 6) == 6


def test_pages_to_process_returns_zero_for_empty_pdf():
    assert pages_to_process(0, 6) == 0
