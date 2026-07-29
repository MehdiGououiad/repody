"""Unit tests for operator Result validators."""

from __future__ import annotations

import json

from repody.runtime.contracts.result import ErrorCode
from repody.runtime.operator.validate import parse_benchmark_options, parse_model_identifier


def test_parse_model_identifier_ok() -> None:
    result = parse_model_identifier("repody:vlm")
    assert result.is_ok
    assert result.unwrap() == "repody:vlm"


def test_parse_model_identifier_rejects_shell() -> None:
    result = parse_model_identifier("model; rm -rf /")
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code == ErrorCode.VALIDATION


def test_parse_benchmark_options_too_many_models() -> None:
    result = parse_benchmark_options(
        profile="models",
        models=json.dumps(["repody:vlm"] * 13),
        validation_mode="logic_only",
        warm_runs=1,
        minimum_accuracy=1.0,
        cache_check=True,
    )
    assert not result.is_ok
    assert result.error is not None
    assert result.error.message == "Select at most 12 models."
