from audit_workbench.services.worker_pool import needs_ocr_pool


def test_needs_ocr_pool_document_model():
    assert needs_ocr_pool("document_model") is True


def test_needs_ocr_pool_unknown_modes_default_to_document_model():
    for mode in ("unknown", "legacy"):
        assert needs_ocr_pool(mode) is True
