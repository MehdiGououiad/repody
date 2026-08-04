"""Official zai-org GLM-OCR SDK (selfhosted + PP-DocLayoutV3).

Docs:
  https://huggingface.co/zai-org/GLM-OCR
  https://github.com/zai-org/GLM-OCR

Self-hosted mode runs PP-DocLayoutV3 region detection, then OCR each region
against an OpenAI-compatible endpoint. Local default is **llama-server**
(ggml-org/GLM-OCR-GGUF on :8083). Optional: Ollama (`api_mode=ollama_generate`
on :11434). NVIDIA: vLLM/SGLang + BF16.

Default config: deploy/glmocr/config.selfhosted.yaml (official label mapping).
Optional ID-card profile: deploy/glmocr/config.idcard.yaml.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog

log = structlog.get_logger()

from repody.extraction.render import GLM_OCR_PDF_DPI

# Official safetensors export referenced by glmocr/config.yaml
DEFAULT_LAYOUT_MODEL = "PaddlePaddle/PP-DocLayoutV3_safetensors"

# Repo-rooted profiles (maas disabled, :8083 openai / optional Ollama).
_REPO_ROOT = Path(__file__).resolve().parents[4]
SELFHOSTED_CONFIG = _REPO_ROOT / "deploy" / "glmocr" / "config.selfhosted.yaml"
ID_CARD_CONFIG = _REPO_ROOT / "deploy" / "glmocr" / "config.idcard.yaml"


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
    id_card_profile: bool = False


_lock = threading.Lock()
_cfg: GlmOcrSdkSettings | None = None
_parser: Any | None = None


def openai_host_port(base_url: str) -> tuple[str, int]:
    """Parse ``AUDIT_GLM_OCR_BASE_URL`` into OCR API host/port for the SDK.

    Ollama default is ``http://127.0.0.1:11434`` (no ``/v1``).
    vLLM / llama.cpp OpenAI-compat roots often end with ``/v1``.
    """
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


def _is_ollama_endpoint(base_url: str, port: int) -> bool:
    """Heuristic: default local Ollama port, or URL without OpenAI ``/v1`` path."""
    if port == 11434:
        return True
    path = (urlparse(base_url if "://" in base_url else f"http://{base_url}").path or "").rstrip(
        "/"
    )
    return path in {"", "/"}


def sdk_importable() -> bool:
    try:
        import glmocr  # noqa: F401
    except ImportError:
        return False
    return True


def _config_path(cfg: GlmOcrSdkSettings) -> Path | None:
    if cfg.id_card_profile and ID_CARD_CONFIG.is_file():
        return ID_CARD_CONFIG
    if SELFHOSTED_CONFIG.is_file():
        return SELFHOSTED_CONFIG
    return None


def _build_parser(cfg: GlmOcrSdkSettings) -> Any:
    from glmocr import GlmOcr

    host, port = openai_host_port(cfg.base_url)
    # Official API: constructor + optional YAML profile + _dotted overrides.
    dotted: dict[str, Any] = {
        "pipeline.ocr_api.request_timeout": cfg.timeout_seconds,
        "pipeline.layout.model_dir": cfg.layout_model_dir,
        "pipeline.max_workers": cfg.max_workers,
        "pipeline.page_loader.pdf_dpi": GLM_OCR_PDF_DPI,
        "pipeline.ocr_api.api_host": host,
        "pipeline.ocr_api.api_port": port,
        "pipeline.ocr_api.model": cfg.model,
        "pipeline.layout.device": cfg.layout_device,
    }
    # Ollama only: native /api/generate (OpenAI-compat vision often 502s).
    # llama-server / vLLM stay on openai + /v1/chat/completions from YAML.
    if _is_ollama_endpoint(cfg.base_url, port):
        dotted["pipeline.ocr_api.api_mode"] = "ollama_generate"
        dotted["pipeline.ocr_api.api_path"] = "/api/generate"
    else:
        dotted["pipeline.ocr_api.api_mode"] = "openai"
        dotted["pipeline.ocr_api.api_path"] = "/v1/chat/completions"
    if cfg.pdf_max_pages is not None:
        dotted["pipeline.page_loader.pdf_max_pages"] = cfg.pdf_max_pages

    kwargs: dict[str, Any] = {
        "mode": "selfhosted",
        "ocr_api_host": host,
        "ocr_api_port": port,
        "model": cfg.model,
        "layout_device": cfg.layout_device,
        "timeout": cfg.timeout_seconds,
        "log_level": "WARNING",
        "_dotted": dotted,
    }
    config_path = _config_path(cfg)
    if config_path is not None:
        kwargs["config_path"] = str(config_path)
    return GlmOcr(**kwargs)


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
            id_card_profile=cfg.id_card_profile,
            config=str(_config_path(cfg)) if _config_path(cfg) else None,
        )
        return _parser


def _region_contents(json_result: Any) -> list[str]:
    """Collect OCR ``content`` strings from official SDK json_result pages."""
    pages = json_result
    if isinstance(pages, str):
        try:
            import json

            pages = json.loads(pages)
        except (TypeError, ValueError):
            return []
    if not isinstance(pages, list):
        return []
    out: list[str] = []
    for page in pages:
        regions = page if isinstance(page, list) else [page]
        for region in regions:
            if not isinstance(region, dict):
                continue
            content = region.get("content")
            if not isinstance(content, str):
                continue
            text = content.strip()
            if not text:
                continue
            # Drop empty fenced placeholders the model sometimes returns for photos.
            if text in {"```markdown\n\n```", "```markdown\n```", "```\n```"}:
                continue
            if text.startswith("```markdown"):
                text = text.removeprefix("```markdown").removesuffix("```").strip()
            if text:
                out.append(text)
    return out


def _markdown_from_result(result: Any, *, region_text_fallback: bool) -> str:
    """Prefer markdown_result; optional ID-card fallback uses region OCR text."""
    markdown = getattr(result, "markdown_result", None)
    md = markdown.strip() if isinstance(markdown, str) else ""
    # Official formatter emits only ![Image …] for label=image and drops OCR text.
    image_only = bool(md) and all(
        line.startswith("![Image ") or not line.strip() for line in md.splitlines()
    )
    if md and not image_only:
        return md
    if region_text_fallback:
        contents = _region_contents(getattr(result, "json_result", None))
        if contents:
            return "\n\n".join(contents)
    return md


def parse_markdown(document_bytes: bytes, *, cfg: GlmOcrSdkSettings) -> str:
    """Run official layout+OCR pipeline; return markdown_result."""
    if not document_bytes:
        raise RuntimeError("GLM-OCR SDK received empty document bytes.")
    parser = _parser_for(cfg)
    result = parser.parse(document_bytes, save_layout_visualization=False)
    markdown = _markdown_from_result(
        result,
        region_text_fallback=cfg.id_card_profile,
    )
    if markdown:
        return markdown
    raise RuntimeError(
        "GLM-OCR SDK returned empty markdown_result. Check llama-server/OCR API on "
        f"{cfg.base_url} and that PP-DocLayoutV3 can load "
        f"({cfg.layout_model_dir})."
    )
