from __future__ import annotations

import shutil
import sys
from pathlib import Path

from audit_workbench.extraction.document_model_branding import public_document_model_label
from audit_workbench.services.operator_benchmark_requests import (
    BUILT_IN_FIXTURE_ROOT,
    BenchmarkRequest,
    OperatorRequestError,
    safe_model_identifier,
)
from audit_workbench.services.operator_jobs import (
    OperatorJob,
    append_output,
    create_job,
    run_command,
)
from audit_workbench.services.operator_benchmark_auth import fetch_operator_benchmark_bearer_token
from audit_workbench.services.operator_reports import load_report


def benchmark_command(
    *,
    document: Path,
    manifest: Path,
    output_dir: Path,
    profile: str,
    models: list[str],
    validation_mode: str,
    warm_runs: int,
    minimum_accuracy: float,
    cache_check: bool,
    judge_quality: bool,
    bearer_token: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        "/app/scripts/benchmark_suite.py",
        "--api",
        "http://127.0.0.1:8000",
        "--document",
        str(document),
        "--manifest",
        str(manifest),
        "--output-dir",
        str(output_dir),
        "--profile",
        profile,
        "--model-validation",
        validation_mode,
        "--warm-runs",
        str(warm_runs),
        "--minimum-accuracy",
        str(minimum_accuracy),
        "--judge-quality" if judge_quality else "--no-judge-quality",
        "--timeout-seconds",
        "900",
        "--continue-on-failure",
        "--cache-check" if cache_check else "--no-cache-check",
    ]
    for model in models:
        command.extend(["--model", model])
    if bearer_token:
        command.extend(["--bearer-token", bearer_token])
    return command


def _promote_latest_report(root: Path, output_dir: Path, job: OperatorJob) -> None:
    latest = output_dir / "latest.json"
    if not latest.is_file():
        return

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


def create_benchmark_job(root: Path, request: BenchmarkRequest) -> OperatorJob:
    options = request.options
    inputs = request.inputs

    async def runner(job: OperatorJob) -> None:
        output_dir = root / f"benchmark-{job.id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        bearer_token = await fetch_operator_benchmark_bearer_token()
        command = benchmark_command(
            document=inputs.document_path,
            manifest=inputs.manifest_path,
            output_dir=output_dir,
            profile=options.profile,
            models=options.models,
            validation_mode=options.validation_mode,
            warm_runs=options.warm_runs,
            minimum_accuracy=options.minimum_accuracy,
            cache_check=options.cache_check,
            judge_quality=options.judge_quality,
            bearer_token=bearer_token,
        )
        command_error: Exception | None = None
        try:
            await run_command(job, command)
        except Exception as exc:
            command_error = exc
        _promote_latest_report(root, output_dir, job)
        if command_error:
            raise command_error
        if not (output_dir / "latest.json").is_file():
            raise RuntimeError("Benchmark completed without a JSON report.")

    return create_job("benchmark", f"{options.profile.title()} benchmark", runner)


def create_warmup_job(
    *,
    root: Path,
    model: str,
    built_in_root: Path = BUILT_IN_FIXTURE_ROOT,
) -> OperatorJob:
    model = safe_model_identifier(model)
    document = built_in_root / "Facture.pdf"
    manifest = built_in_root / "Facture.benchmark.json"
    if not document.is_file() or not manifest.is_file():
        raise OperatorRequestError(503, "Built-in warmup fixture is unavailable.")

    async def runner(job: OperatorJob) -> None:
        output_dir = root / f"warmup-{job.id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        bearer_token = await fetch_operator_benchmark_bearer_token()
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
            judge_quality=False,
            bearer_token=bearer_token,
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

    label = f"Warm up {public_document_model_label(model)}"
    return create_job("model_warmup", label, runner)
