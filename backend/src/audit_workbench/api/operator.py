from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from audit_workbench.inference.http_pool import get_async_http_client
from audit_workbench.services.operator_jobs import (
    OperatorJob,
    append_output,
    benchmark_command,
    create_job,
    get_job,
    list_jobs,
    load_report,
    run_command,
)
from audit_workbench.extraction.document_model_branding import public_document_model_label
from audit_workbench.settings import get_settings

router = APIRouter(prefix="/operator", tags=["operator"])
MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,180}$")
PROFILES = {"quick", "models", "full"}
VALIDATION_MODES = {"logic_only", "logic_and_llm"}


class ModelActionRequest(BaseModel):
    model: str = Field(min_length=1, max_length=180)


def _require_actions() -> None:
    if not get_settings().operator_actions_enabled:
        raise HTTPException(
            status_code=403,
            detail="Operator actions are disabled. Set AUDIT_OPERATOR_ACTIONS_ENABLED=true.",
        )


def _safe_model(model: str) -> str:
    value = model.strip()
    if not MODEL_NAME.fullmatch(value):
        raise HTTPException(status_code=422, detail="Invalid model identifier.")
    return value


def _job_or_404(job_id: str) -> OperatorJob:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Operator job not found.")
    return job


def _operator_root() -> Path:
    root = Path(get_settings().operator_data_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


@router.get("/status")
async def operator_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "actionsEnabled": settings.operator_actions_enabled,
        "reportDirectory": settings.operator_data_path,
        "warmup": {
            "documentModelOnStart": settings.repody_vlm_warmup_on_start,
        },
        "limits": {
            "maxUploadBytes": settings.max_upload_bytes,
            "ocrMaxPages": settings.ocr_max_pages,
            "taskTimeoutMinutes": settings.hatchet_task_timeout_minutes,
        },
    }


@router.get("/jobs")
async def operator_jobs() -> dict[str, Any]:
    return {"jobs": [job.as_dict() for job in list_jobs()]}


@router.get("/jobs/{job_id}")
async def operator_job(job_id: str) -> dict[str, Any]:
    return _job_or_404(job_id).as_dict()


@router.get("/jobs/{job_id}/report")
async def operator_job_report(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)
    if not job.report_path:
        raise HTTPException(status_code=404, detail="This job has no report yet.")
    return load_report(Path(job.report_path))


@router.get("/jobs/{job_id}/artifacts/{artifact}")
async def operator_job_artifact(job_id: str, artifact: str) -> FileResponse:
    job = _job_or_404(job_id)
    if not job.report_path:
        raise HTTPException(status_code=404, detail="This job has no report yet.")
    report_dir = Path(job.report_path).parent
    names = {
        "json": "benchmark-report.json",
        "csv": "benchmark-results.csv",
        "html": "benchmark-report.html",
    }
    name = names.get(artifact)
    if not name or not (path := report_dir / name).is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(path, filename=name)


@router.get("/benchmarks/latest")
async def latest_benchmark() -> dict[str, Any]:
    path = _operator_root() / "latest.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No benchmark report is available.")
    return load_report(path)


@router.post("/models/pull", status_code=202)
async def pull_model(payload: ModelActionRequest) -> dict[str, Any]:
    _require_actions()
    _safe_model(payload.model)
    raise HTTPException(
        status_code=409,
        detail="Install Repody VLM with: pnpm docker:models:pull",
    )


@router.post("/models/warmup", status_code=202)
async def warmup_model(payload: ModelActionRequest) -> dict[str, Any]:
    _require_actions()
    model = _safe_model(payload.model)
    root = _operator_root()
    fixture_root = Path("/app/e2e/fixtures/documents")
    document = fixture_root / "Facture.pdf"
    manifest = fixture_root / "Facture.benchmark.json"
    if not document.is_file() or not manifest.is_file():
        raise HTTPException(status_code=503, detail="Built-in warmup fixture is unavailable.")

    async def runner(job: OperatorJob) -> None:
        output_dir = root / f"warmup-{job.id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        command = benchmark_command(
            document=document,
            manifest=manifest,
            output_dir=output_dir,
            profile="models",
            models=[model],
            validation_mode="logic_only",
            warm_runs=0,
            minimum_accuracy=0.0,
            cache_check=False,
        )
        await run_command(job, command)
        latest = output_dir / "latest.json"
        if latest.is_file():
            report = load_report(latest)
            report_dir = next(
                (
                    child
                    for child in output_dir.iterdir()
                    if child.is_dir() and (child / "benchmark-report.json").is_file()
                ),
                None,
            )
            if report_dir:
                job.report_path = str(report_dir / "benchmark-report.json")
            append_output(job, f"Warmup completed: {report.get('summary', {})}\n")

    job = create_job("model_warmup", f"Warm up {public_document_model_label(model)}", runner)
    return {"job": job.as_dict()}


@router.post("/benchmarks", status_code=202)
async def start_benchmark(
    document: UploadFile | None = File(default=None),
    manifest: UploadFile | None = File(default=None),
    profile: str = Form(default="models"),
    models: str = Form(default="[]"),
    validation_mode: str = Form(default="logic_only"),
    warm_runs: int = Form(default=1, ge=0, le=5),
    minimum_accuracy: float = Form(default=1.0, ge=0.0, le=1.0),
    cache_check: bool = Form(default=True),
) -> dict[str, Any]:
    _require_actions()
    if profile not in PROFILES or validation_mode not in VALIDATION_MODES:
        raise HTTPException(status_code=422, detail="Invalid benchmark options.")
    try:
        selected_models = json.loads(models)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="models must be a JSON array.") from exc
    if not isinstance(selected_models, list) or len(selected_models) > 12:
        raise HTTPException(status_code=422, detail="Select at most 12 models.")
    selected_models = [_safe_model(str(model)) for model in selected_models]

    root = _operator_root()
    built_in = Path("/app/e2e/fixtures/documents")
    if document is None and manifest is None:
        document_path = built_in / "Facture.pdf"
        manifest_path = built_in / "Facture.benchmark.json"
        if not document_path.is_file() or not manifest_path.is_file():
            raise HTTPException(status_code=503, detail="Built-in benchmark fixture is unavailable.")
    elif document is None or manifest is None:
        raise HTTPException(status_code=422, detail="Upload both a document and its JSON manifest.")
    else:
        input_dir = root / "inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(document.filename or "document.pdf").suffix[:10] or ".pdf"
        upload_id = uuid.uuid4().hex[:12]
        stem = re.sub(r"[^A-Za-z0-9._-]", "-", Path(document.filename or "document").stem)
        document_path = input_dir / f"{stem[:40]}-{upload_id}{suffix}"
        manifest_path = input_dir / f"manifest-{upload_id}.json"
        document_bytes = await document.read()
        manifest_bytes = await manifest.read()
        settings = get_settings()
        if not document_bytes or len(document_bytes) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Benchmark document is empty or too large.")
        try:
            json.loads(manifest_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Benchmark manifest must be valid JSON.") from exc
        document_path.write_bytes(document_bytes)
        manifest_path.write_bytes(manifest_bytes)

    async def runner(job: OperatorJob) -> None:
        output_dir = root / f"benchmark-{job.id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        command = benchmark_command(
            document=document_path,
            manifest=manifest_path,
            output_dir=output_dir,
            profile=profile,
            models=selected_models,
            validation_mode=validation_mode,
            warm_runs=warm_runs,
            minimum_accuracy=minimum_accuracy,
            cache_check=cache_check,
        )
        command_error: Exception | None = None
        try:
            await run_command(job, command)
        except Exception as exc:
            command_error = exc
        latest = output_dir / "latest.json"
        if latest.is_file():
            shutil.copyfile(latest, root / "latest.json")
            for extension in ("html", "csv"):
                source = output_dir / f"latest.{extension}"
                if source.is_file():
                    shutil.copyfile(source, root / f"latest.{extension}")
            report_dir = next(
                (
                    child
                    for child in output_dir.iterdir()
                    if child.is_dir() and (child / "benchmark-report.json").is_file()
                ),
                None,
            )
            job.report_path = str((report_dir or output_dir) / "benchmark-report.json")
        if command_error:
            raise command_error
        if not latest.is_file():
            raise RuntimeError("Benchmark completed without a JSON report.")

    job = create_job("benchmark", f"{profile.title()} benchmark", runner)
    return {"job": job.as_dict()}
