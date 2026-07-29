"""Operator request I/O — returns Result; validation in platform.operator.validate."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from audit_workbench.runtime.contracts.result import AppError, ErrorCode, Result
from audit_workbench.runtime.operator.validate import (
    BenchmarkOptions,
    minimal_benchmark_manifest,
    parse_benchmark_options,
    require_operator_actions,
)
from audit_workbench.settings import Settings


class OperatorUpload(Protocol):
    filename: str | None

    async def read(self) -> bytes: ...


@dataclass(frozen=True)
class BenchmarkInputs:
    document_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class BenchmarkRequest:
    inputs: BenchmarkInputs
    options: BenchmarkOptions


def operator_root(settings: Settings) -> Path:
    root = Path(settings.operator_data_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


async def resolve_benchmark_inputs(
    *,
    document: OperatorUpload | None,
    manifest: OperatorUpload | None,
    root: Path,
    max_upload_bytes: int,
) -> Result[BenchmarkInputs]:
    if document is None and manifest is None:
        return Result.fail(
            AppError(
                code=ErrorCode.VALIDATION,
                message="Upload a document (and optional manifest) to benchmark.",
            )
        )

    if document is None:
        return Result.fail(
            AppError(code=ErrorCode.VALIDATION, message="Upload a document to benchmark.")
        )

    input_dir = root / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(document.filename or "document.pdf").suffix[:10] or ".pdf"
    upload_id = uuid.uuid4().hex[:12]
    stem = re.sub(r"[^A-Za-z0-9._-]", "-", Path(document.filename or "document").stem)
    document_path = input_dir / f"{stem[:40]}-{upload_id}{suffix}"
    manifest_path = input_dir / f"manifest-{upload_id}.json"
    document_bytes = await document.read()

    if not document_bytes or len(document_bytes) > max_upload_bytes:
        return Result.fail(
            AppError(
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                message="Benchmark document is empty or too large.",
            )
        )

    document_path.write_bytes(document_bytes)

    if manifest is None:
        manifest_path.write_text(
            json.dumps(minimal_benchmark_manifest(document.filename or document_path.name)),
            encoding="utf-8",
        )
        return Result.ok(BenchmarkInputs(document_path=document_path, manifest_path=manifest_path))

    manifest_bytes = await manifest.read()
    try:
        json.loads(manifest_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return Result.fail(
            AppError(
                code=ErrorCode.VALIDATION,
                message="Benchmark manifest must be valid JSON.",
                cause=str(exc),
            )
        )

    manifest_path.write_bytes(manifest_bytes)
    return Result.ok(BenchmarkInputs(document_path=document_path, manifest_path=manifest_path))


async def build_benchmark_request(
    *,
    document: OperatorUpload | None,
    manifest: OperatorUpload | None,
    root: Path,
    max_upload_bytes: int,
    profile: str,
    models: str,
    validation_mode: str,
    warm_runs: int,
    minimum_accuracy: float,
    cache_check: bool,
    judge_quality: bool = True,
) -> Result[BenchmarkRequest]:
    options = parse_benchmark_options(
        profile=profile,
        models=models,
        validation_mode=validation_mode,
        warm_runs=warm_runs,
        minimum_accuracy=minimum_accuracy,
        cache_check=cache_check,
        judge_quality=judge_quality,
    )
    if not options.is_ok:
        return Result.fail(
            options.error or AppError(code=ErrorCode.VALIDATION, message="Invalid options")
        )
    inputs = await resolve_benchmark_inputs(
        document=document,
        manifest=manifest,
        root=root,
        max_upload_bytes=max_upload_bytes,
    )
    if not inputs.is_ok:
        return Result.fail(
            inputs.error or AppError(code=ErrorCode.VALIDATION, message="Invalid inputs")
        )
    return Result.ok(BenchmarkRequest(inputs=inputs.unwrap(), options=options.unwrap()))


__all__ = [
    "BenchmarkInputs",
    "BenchmarkOptions",
    "BenchmarkRequest",
    "OperatorUpload",
    "build_benchmark_request",
    "operator_root",
    "parse_benchmark_options",
    "require_operator_actions",
    "resolve_benchmark_inputs",
]
