"""Official zai-org GLM-OCR SDK (selfhosted + PP-DocLayoutV3).

Docs:
  https://huggingface.co/zai-org/GLM-OCR
  https://github.com/zai-org/GLM-OCR

Self-hosted mode runs PP-DocLayoutV3 region detection, then OCR each region
against an OpenAI-compatible endpoint (our llama-server GGUF on :8083) with
the official task prompts (Text / Table / Formula Recognition).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import structlog

log = structlog.get_logger()

from repody.extraction.render import GLM_OCR_PDF_DPI

# Official safetensors export referenced by glmocr/config.yaml
DEFAULT_LAYOUT_MODEL = "PaddlePaddle/PP-DocLayoutV3_safetensors"


@dataclass(frozen=True)
class GlmOcrSdkSettings:
    """Connection + layout knobs for one GlmOcr selfhosted session."""

    base_url: str
    model: str
    timeout_seconds: int
    layout_device: str
    layout_model_dir: str
    max_workers: int
    # None → omit override; official glmocr/config.yaml uses pdf_max_pages: null
    pdf_max_pages: int | None = None


_lock = threading.Lock()
_cfg: GlmOcrSdkSettings | None = None
_parser: Any | None = None


def openai_host_port(base_url: str) -> tuple[str, int]:
    """Parse ``AUDIT_GLM_OCR_BASE_URL`` (…/v1) into OCR API host/port for the SDK."""
    raw = (base_url or "").strip()
    if not raw:
        raise ValueError("GLM-OCR base URL is empty")
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        return host, int(parsed.port)
    if parsed.scheme == "https":
        return host, 443
    return host, 80


def sdk_importable() -> bool:
    try:
        import glmocr  # noqa: F401
    except ImportError:
        return False
    return True


def _build_parser(cfg: GlmOcrSdkSettings) -> Any:
    from glmocr import GlmOcr

    host, port = openai_host_port(cfg.base_url)
    # Official API: constructor + _dotted overrides on package config.yaml defaults
    # (task prompts, pdf_dpi, layout label maps, …).
    dotted: dict[str, Any] = {
        "pipeline.ocr_api.request_timeout": cfg.timeout_seconds,
        "pipeline.layout.model_dir": cfg.layout_model_dir,
        "pipeline.max_workers": cfg.max_workers,
        # Pin official package default so upgrades cannot silently change DPI.
        "pipeline.page_loader.pdf_dpi": GLM_OCR_PDF_DPI,
    }
    if cfg.pdf_max_pages is not None:
        dotted["pipeline.page_loader.pdf_max_pages"] = cfg.pdf_max_pages
    return GlmOcr(
        mode="selfhosted",
        ocr_api_host=host,
        ocr_api_port=port,
        model=cfg.model,
        layout_device=cfg.layout_device,
        log_level="WARNING",
        _dotted=dotted,
    )


def _close_parser(parser: Any) -> None:
    if parser is None:
        return
    close = getattr(parser, "close", None)
    if callable(close):
        close()


def close_glm_ocr_sdk() -> None:
    """Drop the process-wide GlmOcr handle (PP-DocLayoutV3 cache)."""
    global _cfg, _parser
    with _lock:
        parser = _parser
        _parser = None
        _cfg = None
    _close_parser(parser)


def reset_glm_ocr_sdk_client() -> None:
    """Test helper — drop the cached GlmOcr instance."""
    close_glm_ocr_sdk()


def _parser_for(cfg: GlmOcrSdkSettings) -> Any:
    global _cfg, _parser
    with _lock:
        if _parser is not None and _cfg == cfg:
            return _parser
        if _parser is not None:
            try:
                _close_parser(_parser)
            except Exception:  # noqa: BLE001 — best-effort swap
                log.warning("glm_ocr_sdk_close_failed", exc_info=True)
        _parser = _build_parser(cfg)
        _cfg = cfg
        log.info(
            "glm_ocr_sdk_ready",
            host_port=openai_host_port(cfg.base_url),
            model=cfg.model,
            layout_device=cfg.layout_device,
            layout_model=cfg.layout_model_dir,
        )
        return _parser


def parse_markdown(document_bytes: bytes, *, cfg: GlmOcrSdkSettings) -> str:
    """Run official layout+OCR pipeline; return markdown_result."""
    if not document_bytes:
        raise RuntimeError("GLM-OCR SDK received empty document bytes.")
    parser = _parser_for(cfg)
    result = parser.parse(document_bytes, save_layout_visualization=False)
    markdown = getattr(result, "markdown_result", None)
    if isinstance(markdown, str) and markdown.strip():
        return markdown.strip()
    raise RuntimeError(
        "GLM-OCR SDK returned empty markdown_result. Check llama-server on "
        f"{cfg.base_url} and that PP-DocLayoutV3 can load "
        f"({cfg.layout_model_dir})."
    )
