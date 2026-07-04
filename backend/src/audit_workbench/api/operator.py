from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from audit_workbench.auth.dependencies import require_permission
from audit_workbench.schemas.operator import (
    BenchmarkReportSchema,
    OperatorJobAcceptedResponse,
    OperatorJobSchema,
    OperatorJobsResponse,
    OperatorStatusResponse,
    OperatorLimitsSchema,
    OperatorWarmupConfig,
)
from audit_workbench.schemas.operator_requests import ModelActionRequest
from audit_workbench.services.operator import (
    OperatorRequestError,
    create_benchmark_job,
    create_warmup_job,
    get_job,
    list_jobs,
    load_report,
    operator_job_schema,
    safe_model_identifier,
)
from audit_workbench.services.operator.requests import (
    build_benchmark_request,
    operator_root,
    require_operator_actions,
)
from audit_workbench.settings import get_settings

router = APIRouter(prefix="/operator", tags=["operator"])


def _require_actions() -> None:
    try:
        require_operator_actions(get_settings())
    except OperatorRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _safe_model(model: str) -> str:
    try:
        return safe_model_identifier(model)
    except OperatorRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _job_or_404(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Operator job not found.")
    return job


def _operator_root() -> Path:
    return operator_root(get_settings())


def _raise_operator_error(exc: OperatorRequestError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/status",
    response_model=OperatorStatusResponse,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def operator_status() -> OperatorStatusResponse:
    settings = get_settings()
    return OperatorStatusResponse(
        actions_enabled=settings.operator_actions_enabled,
        report_directory=settings.operator_data_path,
        warmup=OperatorWarmupConfig(
            document_model_on_start=settings.repody_vlm_warmup_on_start,
        ),
        limits=OperatorLimitsSchema(
            max_upload_bytes=settings.max_upload_bytes,
            ocr_max_pages=settings.ocr_max_pages,
            task_timeout_minutes=settings.worker_task_timeout_minutes,
        ),
    )


@router.get(
    "/jobs",
    response_model=OperatorJobsResponse,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def operator_jobs() -> OperatorJobsResponse:
    return OperatorJobsResponse(jobs=[operator_job_schema(job) for job in list_jobs()])


@router.get(
    "/jobs/{job_id}",
    response_model=OperatorJobSchema,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def operator_job(job_id: str) -> OperatorJobSchema:
    return operator_job_schema(_job_or_404(job_id))


@router.get(
    "/jobs/{job_id}/report",
    response_model=BenchmarkReportSchema,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def operator_job_report(job_id: str) -> BenchmarkReportSchema:
    job = _job_or_404(job_id)
    if not job.report_path:
        raise HTTPException(status_code=404, detail="This job has no report yet.")
    return BenchmarkReportSchema.model_validate(load_report(Path(job.report_path)))


@router.get(
    "/jobs/{job_id}/artifacts/{artifact}",
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
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


@router.get(
    "/benchmarks/latest",
    response_model=BenchmarkReportSchema,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def latest_benchmark() -> BenchmarkReportSchema:
    path = _operator_root() / "latest.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No benchmark report is available.")
    return BenchmarkReportSchema.model_validate(load_report(path))


@router.post(
    "/models/warmup",
    status_code=202,
    response_model=OperatorJobAcceptedResponse,
    dependencies=[Depends(require_permission("operator", "execute"))],
)
async def warmup_model(payload: ModelActionRequest) -> OperatorJobAcceptedResponse:
    _require_actions()
    _safe_model(payload.model)
    root = _operator_root()
    try:
        job = create_warmup_job(root=root, model=payload.model)
    except OperatorRequestError as exc:
        _raise_operator_error(exc)
    return OperatorJobAcceptedResponse(job=operator_job_schema(job))


@router.post(
    "/benchmarks",
    status_code=202,
    response_model=OperatorJobAcceptedResponse,
    dependencies=[Depends(require_permission("operator", "execute"))],
)
async def start_benchmark(
    document: UploadFile | None = File(default=None),
    manifest: UploadFile | None = File(default=None),
    profile: str = Form(default="models"),
    models: str = Form(default="[]"),
    validation_mode: str = Form(default="logic_only"),
    warm_runs: int = Form(default=1, ge=0, le=5),
    minimum_accuracy: float = Form(default=1.0, ge=0.0, le=1.0),
    cache_check: bool = Form(default=True),
    judge_quality: bool = Form(default=True),
) -> OperatorJobAcceptedResponse:
    _require_actions()
    root = _operator_root()
    try:
        benchmark_request = await build_benchmark_request(
            document=document,
            manifest=manifest,
            root=root,
            max_upload_bytes=get_settings().max_upload_bytes,
            profile=profile,
            models=models,
            validation_mode=validation_mode,
            warm_runs=warm_runs,
            minimum_accuracy=minimum_accuracy,
            cache_check=cache_check,
            judge_quality=judge_quality,
        )
        job = create_benchmark_job(root, benchmark_request)
    except OperatorRequestError as exc:
        _raise_operator_error(exc)
    return OperatorJobAcceptedResponse(job=operator_job_schema(job))
