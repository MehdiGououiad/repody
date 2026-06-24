"""Tests for Surya OCR 2 text conversion helpers."""

from __future__ import annotations

import asyncio

from audit_workbench.extraction.document_model_branding import (
    SURYA_OCR2_CATALOG_ID,
    is_legacy_catalog_id,
)
from audit_workbench.extraction.model_registry import (
    is_ocr_compare_model,
    parse_document_model,
)
from audit_workbench.extraction.surya_ocr import (
    _predictions_to_text,
    _run_surya_pipeline,
    _table_results_to_text,
    build_surya_env_updates,
    extract_with_surya_ocr2,
    surya_inference_configured,
)


def test_predictions_to_text_from_block_dicts():
    predictions = [
        {
            "blocks": [
                {"html": "<div>Invoice <b>123</b></div>", "skipped": False},
                {"html": "", "skipped": True},
            ]
        }
    ]
    text = _predictions_to_text(predictions)
    assert "Invoice" in text
    assert "123" in text
    assert "## Page 1" in text


def test_surya_catalog_id_is_not_legacy():
    assert not is_legacy_catalog_id(SURYA_OCR2_CATALOG_ID)
    assert is_legacy_catalog_id("repody/repody-vlm:old-tag")


def test_surya_registered_as_ocr_compare(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    spec = parse_document_model(SURYA_OCR2_CATALOG_ID)
    assert spec.compare_only is True
    assert spec.workflow_selectable is True
    assert spec.markdown_only is True
    assert is_ocr_compare_model(SURYA_OCR2_CATALOG_ID)
    assert surya_inference_configured()
    get_settings.cache_clear()


def test_surya_requires_inference_url(monkeypatch):
    monkeypatch.delenv("AUDIT_SURYA_INFERENCE_URL", raising=False)
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    assert not surya_inference_configured()
    get_settings.cache_clear()


def test_build_surya_env_updates_upstream_defaults(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    updates = build_surya_env_updates(settings)
    assert updates["IMAGE_DPI"] == "96"
    assert updates["IMAGE_DPI_HIGHRES"] == "192"
    assert updates["SURYA_MAX_TOKENS_FULL_PAGE"] == "12288"
    assert updates["DETECTOR_TEXT_THRESHOLD"] == "0.6"
    assert updates["SURYA_INFERENCE_PARALLEL"] == "8"
    get_settings.cache_clear()


def test_table_results_to_text_from_html():
    class _Result:
        html = "<table><tr><td>Amount</td><td>100</td></tr></table>"
        error = False

    text = _table_results_to_text([_Result()])
    assert "Amount" in text
    assert "100" in text
    assert "## Page 1 (tables)" in text


def test_run_surya_pipeline_full_page_default(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("AUDIT_SURYA_LAYOUT_BLOCK_OCR_ENABLED", "false")
    monkeypatch.setenv("AUDIT_SURYA_TABLE_RECOGNITION_ENABLED", "false")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    recognition_calls: list[tuple] = []

    class FakePage:
        blocks = [{"html": "<div>full page</div>", "skipped": False}]

    class FakeRecognitionPredictor:
        def __init__(self, _manager):
            pass

        def __call__(self, images, layout_results=None, *, full_page=None):
            recognition_calls.append((len(images), layout_results, full_page))
            return [FakePage()]

    _install_fake_surya(monkeypatch, recognition=FakeRecognitionPredictor)
    text = _run_surya_pipeline(["img"], settings)
    assert "full page" in text
    assert recognition_calls == [(1, None, None)]
    get_settings.cache_clear()


def test_surya_markdown_workflow_returns_ocr_text(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()

    class _Bundle:
        mime_type = "image/png"
        raw_bytes = b"png"
        page_count = 1

    monkeypatch.setattr(
        "audit_workbench.extraction.surya_ocr.surya_package_installed",
        lambda: True,
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.surya_ocr.surya_pil_pages",
        lambda bundle, settings: [object()],
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.surya_ocr._run_surya_pipeline",
        lambda page_images, settings: "line one",
    )
    result = asyncio.run(
        extract_with_surya_ocr2(_Bundle(), [], "Invoice", markdown_extraction=True)
    )
    assert result.ocr_text is not None
    assert "line one" in result.ocr_text
    assert result.raw_text is None
    get_settings.cache_clear()


def test_run_surya_pipeline_layout_block_and_table(monkeypatch):
    monkeypatch.setenv("AUDIT_SURYA_INFERENCE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("AUDIT_SURYA_LAYOUT_BLOCK_OCR_ENABLED", "true")
    monkeypatch.setenv("AUDIT_SURYA_TABLE_RECOGNITION_ENABLED", "true")
    from audit_workbench.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    layout_calls: list[int] = []
    recognition_calls: list[tuple] = []
    table_calls: list[int] = []

    class FakePage:
        blocks = [{"html": "<div>block ocr</div>", "skipped": False}]

    class FakeLayoutPredictor:
        def __init__(self, _manager):
            pass

        def __call__(self, images):
            layout_calls.append(len(images))
            return ["layout"] * len(images)

    class FakeRecognitionPredictor:
        def __init__(self, _manager):
            pass

        def __call__(self, images, layout_results=None, *, full_page=None):
            recognition_calls.append((len(images), layout_results, full_page))
            return [FakePage()]

    class FakeTableRecPredictor:
        def __init__(self, _manager):
            pass

        def predict_full(self, images):
            table_calls.append(len(images))

            class _Result:
                html = "<table><tr><td>cell</td></tr></table>"
                error = False

            return [_Result()]

    _install_fake_surya(
        monkeypatch,
        layout=FakeLayoutPredictor,
        recognition=FakeRecognitionPredictor,
        table=FakeTableRecPredictor,
    )
    text = _run_surya_pipeline(["img"], settings)
    assert "block ocr" in text
    assert "cell" in text
    assert layout_calls == [1]
    assert recognition_calls == [(1, ["layout"], False)]
    assert table_calls == [1]
    get_settings.cache_clear()


def _install_fake_surya(monkeypatch, *, layout=None, recognition=None, table=None):
    import sys
    from types import ModuleType

    class FakeManager:
        pass

    fake_inference = ModuleType("surya.inference")
    fake_inference.SuryaInferenceManager = FakeManager
    monkeypatch.setitem(sys.modules, "surya.inference", fake_inference)

    if layout is not None:
        fake_layout = ModuleType("surya.layout")
        fake_layout.LayoutPredictor = layout
        monkeypatch.setitem(sys.modules, "surya.layout", fake_layout)

    if recognition is not None:
        fake_recognition = ModuleType("surya.recognition")
        fake_recognition.RecognitionPredictor = recognition
        monkeypatch.setitem(sys.modules, "surya.recognition", fake_recognition)

    if table is not None:
        fake_table = ModuleType("surya.table_rec")
        fake_table.TableRecPredictor = table
        monkeypatch.setitem(sys.modules, "surya.table_rec", fake_table)
