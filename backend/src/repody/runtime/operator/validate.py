"""Operator validate — Result / AppError only (no exception bridges)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.settings import Settings

MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,180}$")
PROFILES = frozenset({"quick", "models", "full"})
VALIDATION_MODES = frozenset({"logic_only", "logic_and_llm"})

_MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


@dataclass(frozen=True, slots=True)
class BenchmarkOptions:
    profile: str
    models: list[str]
    validation_mode: str
    warm_runs: int
    minimum_accuracy: float
    cache_check: bool
    judge_quality: bool = True


def require_operator_actions(settings: Settings) -> Result[None]:
    if not settings.operator_actions_enabled:
        return Result.fail(
            AppError(
                code=ErrorCode.FORBIDDEN,
                message=("Operator actions are disabled. Set AUDIT_OPERATOR_ACTIONS_ENABLED=true."),
            )
        )
    return Result.ok(None)


def minimal_benchmark_manifest(filename: str) -> dict[str, object]:
    path = Path(filename or "document.pdf")
    return {
        "name": path.name,
        "documentType": "Document",
        "mimeType": _MIME_BY_SUFFIX.get(path.suffix.lower(), "application/pdf"),
        "fields": [],
        "baselineFields": [],
        "logicRules": [],
        "logicValidationRules": [],
        "llmValidationRules": [],
    }


def parse_model_identifier(model: str) -> Result[str]:
    value = model.strip()
    if not MODEL_NAME.fullmatch(value):
        return Result.fail(AppError(code=ErrorCode.VALIDATION, message="Invalid model identifier."))
    return Result.ok(value)


def parse_benchmark_options(
    *,
    profile: str,
    models: str,
    validation_mode: str,
    warm_runs: int,
    minimum_accuracy: float,
    cache_check: bool,
    judge_quality: bool = True,
) -> Result[BenchmarkOptions]:
    if profile not in PROFILES or validation_mode not in VALIDATION_MODES:
        return Result.fail(
            AppError(code=ErrorCode.VALIDATION, message="Invalid benchmark options.")
        )
    try:
        selected_models = json.loads(models)
    except json.JSONDecodeError as exc:
        return Result.fail(
            AppError(
                code=ErrorCode.VALIDATION,
                message="models must be a JSON array.",
                cause=str(exc),
            )
        )
    if not isinstance(selected_models, list) or len(selected_models) > 12:
        return Result.fail(AppError(code=ErrorCode.VALIDATION, message="Select at most 12 models."))
    parsed_models: list[str] = []
    for model in selected_models:
        mid = parse_model_identifier(str(model))
        if not mid.is_ok:
            return Result.fail(
                mid.error or AppError(code=ErrorCode.VALIDATION, message="Invalid model")
            )
        parsed_models.append(mid.unwrap())
    return Result.ok(
        BenchmarkOptions(
            profile=profile,
            models=parsed_models,
            validation_mode=validation_mode,
            warm_runs=warm_runs,
            minimum_accuracy=minimum_accuracy,
            cache_check=cache_check,
            judge_quality=judge_quality,
        )
    )
