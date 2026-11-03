"""Tests for serverless GPU cold-start heuristics."""

from __future__ import annotations

from repody.inference.runtime import (
    GPU_COLD_START_THRESHOLD_MS,
    gpu_cold_start_likely,
    is_serverless_inference,
)
from repody.settings import Settings


def _settings(base_url: str) -> Settings:
    return Settings(llamacpp_base_url=base_url)


def test_is_serverless_inference():
    assert is_serverless_inference(_settings("https://runpod.example/v1"))
    assert not is_serverless_inference(_settings("http://127.0.0.1:8081/v1"))
    assert not is_serverless_inference(_settings("http://host.docker.internal:8081/v1"))


def test_gpu_cold_start_likely():
    remote = _settings("https://runpod.example/v1")
    local = _settings("http://host.docker.internal:8081/v1")
    threshold = GPU_COLD_START_THRESHOLD_MS
    assert gpu_cold_start_likely(threshold, settings=remote)
    assert not gpu_cold_start_likely(threshold, settings=local)
    assert not gpu_cold_start_likely(threshold - 1, settings=remote)
