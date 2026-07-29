"""Select stub vs validation chat / availability callables."""

from __future__ import annotations

from functools import lru_cache

from repody.inference.base import ChatFn, EnsureAvailableFn
from repody.inference.stub import chat_stub, ensure_stub_available
from repody.inference.validation_client import (
    chat_validation,
    ensure_validation_available,
)
from repody.settings import get_settings


@lru_cache
def get_chat() -> ChatFn:
    if get_settings().inference_mode.lower() == "stub":
        return chat_stub
    return chat_validation


@lru_cache
def get_ensure_available() -> EnsureAvailableFn:
    if get_settings().inference_mode.lower() == "stub":
        return ensure_stub_available
    return ensure_validation_available
