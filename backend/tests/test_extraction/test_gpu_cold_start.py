"""Tests for serverless GPU cold-start heuristics."""

from __future__ import annotations

from audit_workbench.extraction.gpu_cold_start import (
    GPU_COLD_START_THRESHOLD_MS,
    gpu_cold_start_likely,
    is_serverless_inference,
)


class _Settings:
    inference_mode: str
    llamacpp_base_url: str

    def __init__(self, mode: str, base_url: str = "https://runpod.example/v1") -> None:
        self.inference_mode = mode
        self.llamacpp_base_url = base_url


def test_is_serverless_inference():
    assert is_serverless_inference(_Settings("llamacpp", "https://runpod.example/v1"))
    assert not is_serverless_inference(_Settings("llamacpp", "http://127.0.0.1:8081/v1"))
    assert not is_serverless_inference(_Settings("llamacpp", "http://host.docker.internal:8081/v1"))
    assert not is_serverless_inference(_Settings("docker"))


def test_gpu_cold_start_likely():
    remote = _Settings("llamacpp", "https://runpod.example/v1")
    local = _Settings("llamacpp", "http://host.docker.internal:8081/v1")
    threshold = GPU_COLD_START_THRESHOLD_MS
    assert gpu_cold_start_likely(threshold, settings=remote)
    assert not gpu_cold_start_likely(threshold, settings=local)
    assert not gpu_cold_start_likely(threshold - 1, settings=remote)
    assert not gpu_cold_start_likely(threshold, cache_hit=True, settings=remote)
    assert not gpu_cold_start_likely(threshold, settings=_Settings("docker"))
