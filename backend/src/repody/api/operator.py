from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from repody.api.auth import require_permission
from repody.api.errors import unwrap_or_raise
from repody.app.operator.benchmarks import (
    create_benchmark_job,
    create_warmup_job,
)
from repody.app.operator.jobs import (
    get_job,
    list_jobs,
    load_report,
    operator_job_schema,
)
from repody.app.operator.requests import (
    build_benchmark_request,
    operator_root,
)
from repody.runtime.operator.validate import (
    parse_model_identifier,
    require_operator_actions,
)
from repody.schemas.operator import (
    BenchmarkReportSchema,
    OperatorJobAcceptedResponse,
    OperatorJobSchema,
    OperatorJobsResponse,
    OperatorLimitsSchema,
    OperatorStatusResponse,
    OperatorWarmupConfig,
)
from repody.schemas.operator_requests import ModelActionRequest
from repody.settings import get_settings

router = APIRouter(prefix="/operator", tags=["operator"])


def _job_or_404(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Operator job not found.")
    return job


def _report_path_or_404(job_id: str) -> Path:
    job = _job_or_404(job_id)
    if not job.report_path:
        raise HTTPException(404, "This job has no report yet.")
    return Path(job.report_path)


def _operator_root() -> Path:
    return operator_root(get_settings())


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
            nuextract_max_pages_per_request=settings.repody_vlm_max_pages_per_request,
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
    return BenchmarkReportSchema.model_validate(load_report(_report_path_or_404(job_id)))


@router.get(
    "/jobs/{job_id}/artifacts/{artifact}",
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def operator_job_artifact(job_id: str, artifact: str) -> FileResponse:
    report_dir = _report_path_or_404(job_id).parent
    names = {
        "json": "benchmark-report.json",
        "csv": "benchmark-results.csv",
        "html": "benchmark-report.html",
    }
    name = names.get(artifact)
    if not name or not (path := report_dir / name).is_file():
        raise HTTPException(404, "Artifact not found.")
    return FileResponse(path, filename=name)


@router.get(
    "/benchmarks/latest",
    response_model=BenchmarkReportSchema,
    dependencies=[Depends(require_permission("diagnostics", "read"))],
)
async def latest_benchmark() -> BenchmarkReportSchema:
    path = _operator_root() / "latest.json"
    if not path.is_file():
        raise HTTPException(404, "No benchmark report is available.")
    return BenchmarkReportSchema.model_validate(load_report(path))


@router.post(
    "/models/warmup",
    status_code=202,
    response_model=OperatorJobAcceptedResponse,
    dependencies=[Depends(require_permission("operator", "execute"))],
)
async def warmup_model(payload: ModelActionRequest) -> OperatorJobAcceptedResponse:
    unwrap_or_raise(require_operator_actions(get_settings()))
    model = unwrap_or_raise(parse_model_identifier(payload.model))
    root = _operator_root()
    job = create_warmup_job(root=root, model=model)
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
    unwrap_or_raise(require_operator_actions(get_settings()))
    root = _operator_root()
    built = await build_benchmark_request(
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
    job = create_benchmark_job(root, unwrap_or_raise(built))
    return OperatorJobAcceptedResponse(job=operator_job_schema(job))
