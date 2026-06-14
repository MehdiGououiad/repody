from __future__ import annotations

from typing import Any

from audit_workbench.inference.base import InferenceClient


class StubInferenceClient(InferenceClient):
    @property
    def is_available(self) -> bool:
        return False

    async def chat(self, messages: list[dict[str, Any]], **opts: Any) -> str:
        _ = messages, opts
        return '{"passed": true, "detail": "Inference disabled (stub mode)."}'
