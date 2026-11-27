"""Swappable ``VisualExplainer`` implementations (disabled by default)."""

import base64

import httpx
import structlog

from repody_common.contracts import FraudFinding
from repody_fraud.settings import get_settings

log = structlog.get_logger(__name__)


class OpenAIVisualExplainer:
    """Optional Qwen3-VL Apache-2.0 explainer over an OpenAI-compatible on-prem server."""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def explain_region(
        self,
        image_png: bytes,
        findings: list[FraudFinding],
    ) -> str | None:
        b64 = base64.b64encode(image_png).decode("ascii")
        summary = "; ".join(f"{f.code}: {f.detail}" for f in findings[:4])
        payload = {
            "model": self._model,
            "max_tokens": 256,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Write a concise forensic analyst note describing the visual "
                                f"anomalies highlighted in this document overlay. Findings: {summary}"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
                return str(body["choices"][0]["message"]["content"]).strip()
        except Exception as exc:
            log.warning("visual_explainer_failed", error=repr(exc))
            return None


def build_explainer() -> OpenAIVisualExplainer | None:
    """Instantiate configured explainer from settings, or None when disabled."""
    settings = get_settings()
    if not settings.explainer_base_url:
        return None
    key = settings.explainer_api_key.get_secret_value() if settings.explainer_api_key else "local"
    return OpenAIVisualExplainer(
        base_url=settings.explainer_base_url,
        api_key=key,
        model=settings.explainer_model,
    )
