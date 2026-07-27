"""Inference chat callables — no client ABC."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ChatFn = Callable[..., Awaitable[str]]
EnsureAvailableFn = Callable[[], Awaitable[bool]]
