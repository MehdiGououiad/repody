"""Tests for serverless GPU cold-start heuristics."""

from __future__ import annotations

from audit_workbench.extraction.gpu_cold_start import (
    GPU_COLD_START_THRESHOLD_MS,
    gpu_cold_start_likely,
    is_serverless_vllm,
)


class _Settings:
    inference_mode: str

    def __init__(self, mode: str) -> None:
        self.inference_mode = mode


def test_is_serverless_vllm():
    assert is_serverless_vllm(_Settings("vllm"))
    assert not is_serverless_vllm(_Settings("docker"))


def test_gpu_cold_start_likely():
    settings = _Settings("vllm")
    threshold = GPU_COLD_START_THRESHOLD_MS
    assert gpu_cold_start_likely(threshold, settings=settings)
    assert not gpu_cold_start_likely(threshold - 1, settings=settings)
    assert not gpu_cold_start_likely(threshold, cache_hit=True, settings=settings)
    assert not gpu_cold_start_likely(threshold, settings=_Settings("docker"))
