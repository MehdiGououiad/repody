from audit_workbench.extraction.ocr_markdown import normalize_ocr_markdown


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
