from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from audit_workbench.settings import Settings

MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,180}$")
PROFILES = {"quick", "models", "full"}
VALIDATION_MODES = {"logic_only", "logic_and_llm"}
BUILT_IN_FIXTURE_ROOT = Path("/app/e2e/fixtures/documents")

_MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def minimal_benchmark_manifest(filename: str) -> dict[str, object]:
    """Workflow stub for markdown/OCR compare — no expected fields or rules."""
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


class OperatorUpload(Protocol):
    filename: str | None

    async def read(self) -> bytes: ...


@dataclass
class OperatorRequestError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class BenchmarkOptions:
    profile: str
    models: list[str]
    validation_mode: str
    warm_runs: int
    minimum_accuracy: float
    cache_check: bool
    judge_quality: bool = True


@dataclass(frozen=True)
class BenchmarkInputs:
    document_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class BenchmarkRequest:
    inputs: BenchmarkInputs
    options: BenchmarkOptions


def require_operator_actions(settings: Settings) -> None:
    if not settings.operator_actions_enabled:
        raise OperatorRequestError(
            403,
            "Operator actions are disabled. Set AUDIT_OPERATOR_ACTIONS_ENABLED=true.",
        )


def operator_root(settings: Settings) -> Path:
    root = Path(settings.operator_data_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_model_identifier(model: str) -> str:
    value = model.strip()
    if not MODEL_NAME.fullmatch(value):
        raise OperatorRequestError(422, "Invalid model identifier.")
    return value


def parse_benchmark_options(
    *,
    profile: str,
    models: str,
    validation_mode: str,
    warm_runs: int,
    minimum_accuracy: float,
    cache_check: bool,
    judge_quality: bool = True,
) -> BenchmarkOptions:
    if profile not in PROFILES or validation_mode not in VALIDATION_MODES:
        raise OperatorRequestError(422, "Invalid benchmark options.")
    try:
        selected_models = json.loads(models)
    except json.JSONDecodeError as exc:
        raise OperatorRequestError(422, "models must be a JSON array.") from exc
    if not isinstance(selected_models, list) or len(selected_models) > 12:
        raise OperatorRequestError(422, "Select at most 12 models.")
    return BenchmarkOptions(
        profile=profile,
        models=[safe_model_identifier(str(model)) for model in selected_models],
        validation_mode=validation_mode,
        warm_runs=warm_runs,
        minimum_accuracy=minimum_accuracy,
        cache_check=cache_check,
        judge_quality=judge_quality,
    )


async def resolve_benchmark_inputs(
    *,
    document: OperatorUpload | None,
    manifest: OperatorUpload | None,
    root: Path,
    max_upload_bytes: int,
    built_in_root: Path = BUILT_IN_FIXTURE_ROOT,
) -> BenchmarkInputs:
    if document is None and manifest is None:
        document_path = built_in_root / "Facture.pdf"
        manifest_path = built_in_root / "Facture.benchmark.json"
        if not document_path.is_file() or not manifest_path.is_file():
            raise OperatorRequestError(503, "Built-in benchmark fixture is unavailable.")
        return BenchmarkInputs(document_path=document_path, manifest_path=manifest_path)

    if document is None:
        raise OperatorRequestError(422, "Upload a document to benchmark.")

    input_dir = root / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(document.filename or "document.pdf").suffix[:10] or ".pdf"
    upload_id = uuid.uuid4().hex[:12]
    stem = re.sub(r"[^A-Za-z0-9._-]", "-", Path(document.filename or "document").stem)
    document_path = input_dir / f"{stem[:40]}-{upload_id}{suffix}"
    manifest_path = input_dir / f"manifest-{upload_id}.json"
    document_bytes = await document.read()

    if not document_bytes or len(document_bytes) > max_upload_bytes:
        raise OperatorRequestError(413, "Benchmark document is empty or too large.")

    document_path.write_bytes(document_bytes)

    if manifest is None:
        manifest_path.write_text(
            json.dumps(minimal_benchmark_manifest(document.filename or document_path.name)),
            encoding="utf-8",
        )
        return BenchmarkInputs(document_path=document_path, manifest_path=manifest_path)

    manifest_bytes = await manifest.read()
    try:
        json.loads(manifest_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OperatorRequestError(422, "Benchmark manifest must be valid JSON.") from exc

    manifest_path.write_bytes(manifest_bytes)
    return BenchmarkInputs(document_path=document_path, manifest_path=manifest_path)


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
) -> BenchmarkRequest:
    options = parse_benchmark_options(
        profile=profile,
        models=models,
        validation_mode=validation_mode,
        warm_runs=warm_runs,
        minimum_accuracy=minimum_accuracy,
        cache_check=cache_check,
        judge_quality=judge_quality,
    )
    inputs = await resolve_benchmark_inputs(
        document=document,
        manifest=manifest,
        root=root,
        max_upload_bytes=max_upload_bytes,
    )
    return BenchmarkRequest(inputs=inputs, options=options)
