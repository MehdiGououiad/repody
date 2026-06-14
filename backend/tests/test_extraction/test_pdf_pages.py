from audit_workbench.extraction.pdf_pages import (
    effective_pdf_page_limit,
    join_page_texts,
    pages_to_process,
)


def test_join_page_texts_single_page():
    assert join_page_texts(["hello world"]) == "hello world"


def test_join_page_texts_multi_page():
    joined = join_page_texts(["page one", "page two"])
    assert "--- Page 1 ---" in joined
    assert "--- Page 2 ---" in joined
    assert "page one" in joined
    assert "page two" in joined


def test_pages_to_process_respects_limit():
    assert pages_to_process(20, 10) == 10
    assert pages_to_process(5, 10) == 5


def test_pages_to_process_zero_means_hard_cap():
    assert pages_to_process(100, 0, hard_cap=50) == 50


def test_effective_pdf_page_limit():
    assert effective_pdf_page_limit(10) == 10
    assert effective_pdf_page_limit(0, hard_cap=50) == 50
