from __future__ import annotations

import shutil
import sys
from pathlib import Path

from repody.app.operator.auth import fetch_operator_benchmark_bearer_token
from repody.app.operator.jobs import append_output, create_job, run_command
from repody.app.operator.requests import BenchmarkRequest
from repody.extraction.branding import public_document_model_label
from repody.extraction.warmup import warmup_repody_vlm
from repody.runtime.operator.job import OperatorJob
from repody.runtime.operator.validate import parse_model_identifier

# Image layout from backend/Dockerfile; running from here puts the scripts package on sys.path.
APP_ROOT = Path("/app")


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
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "scripts.benchmark_suite",
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
        )
        command_error: Exception | None = None
        try:
            # The suite reads AUDIT_BENCHMARK_BEARER_TOKEN. Keep it off argv.
            await run_command(
                job,
                command,
                cwd=APP_ROOT,
                env={"AUDIT_BENCHMARK_BEARER_TOKEN": bearer_token} if bearer_token else None,
            )
        except Exception as exc:
            command_error = exc
        _promote_latest_report(root, output_dir, job)
        if command_error:
            raise command_error
        if not (output_dir / "latest.json").is_file():
            raise RuntimeError("Benchmark completed without a JSON report.")

    return create_job("benchmark", f"{options.profile.title()} benchmark", runner)


def create_warmup_job(*, root: Path, model: str) -> OperatorJob:
    _ = root
    parsed = parse_model_identifier(model)
    if not parsed.is_ok:
        raise ValueError(parsed.error.message if parsed.error else "Invalid model")
    model = parsed.unwrap()

    async def runner(job: OperatorJob) -> None:
        append_output(job, f"Warming up {public_document_model_label(model)}...\n")
        result = await warmup_repody_vlm()
        append_output(job, f"Warmup finished: {result}\n")
        if result == "failed":
            raise RuntimeError("Repody VLM warmup failed")

    label = f"Warm up {public_document_model_label(model)}"
    return create_job("model_warmup", label, runner)
