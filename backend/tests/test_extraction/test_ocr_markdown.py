from audit_workbench.extraction.ocr_markdown import format_plain_ocr_lines, normalize_ocr_markdown


def test_html_table_to_markdown():
    html = """
    <table border="1">
      <tr><td>Description</td><td>Qty</td><td>Total TTC</td></tr>
      <tr><td>Ordinateur</td><td>1</td><td>6 000.00</td></tr>
    </table>
    """
    out = normalize_ocr_markdown(html)
    assert "| Description | Qty | Total TTC |" in out
    assert "| Ordinateur | 1 | 6 000.00 |" in out


def test_runon_totals_split():
    raw = "Total HT 5 000,00Total TVA 1 000.00Total TTC 6 000,00"
    out = normalize_ocr_markdown(raw)
    assert "Total HT" in out
    assert "Total TVA" in out
    assert "Total TTC" in out
    assert out.count("\n") >= 2


def test_plain_ocr_lines_use_paragraph_breaks():
    out = format_plain_ocr_lines(["Invoice number: INV-42", "Total TTC: 6000,00 MAD"])
    assert "**Invoice number:** INV-42" in out
    assert "**Total TTC:** 6000,00 MAD" in out
    assert "\n\n" in out


def test_plain_ocr_page_sections_keep_headers():
    raw = "## Page 1\nInvoice number: INV-42\n\n## Page 2\nClient: ACME"
    out = normalize_ocr_markdown(raw)
    assert "## Page 1" in out
    assert "## Page 2" in out
    assert "**Invoice number:** INV-42" in out
    assert "**Client:** ACME" in out


def test_nuextract_markdown_converts_tables_and_figures():
    raw = """
<figure data-type="image"><img src="x.png" alt="Company logo"/></figure>

# INVOICE
**Sold to** ACME Corp

<table>
  <tr><th>Item</th><th>Qty</th></tr>
  <tr><td>Widget</td><td>2</td></tr>
</table>
"""
    out = normalize_ocr_markdown(raw)
    assert "# INVOICE" in out
    assert "*[Image: Company logo]*" in out
    assert "| Item | Qty |" in out
    assert "| Widget | 2 |" in out


def test_structured_markdown_skips_plain_line_reformatting():
    raw = "# Title\n\n**Label** value"
    out = normalize_ocr_markdown(raw)
    assert out == "# Title\n\n**Label** value"
