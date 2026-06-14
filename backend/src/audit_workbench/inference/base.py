from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InferenceClient(ABC):
    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def chat(self, messages: list[dict[str, Any]], **opts: Any) -> str: ...

    async def ensure_available(self) -> bool:
        ping = getattr(self, "ping", None)
        if ping is not None:
            return await ping()
        return self.is_available

    async def chat_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        *,
        mime_type: str = "image/jpeg",
        **opts: Any,
    ) -> str:
        _ = prompt, image_bytes, mime_type, opts
        raise NotImplementedError(f"{type(self).__name__} does not support vision")
