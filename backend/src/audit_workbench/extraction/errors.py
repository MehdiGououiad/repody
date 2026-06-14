from __future__ import annotations


class OcrEngineError(RuntimeError):
    """Raised when OCR fails — callers should not treat as empty text."""
