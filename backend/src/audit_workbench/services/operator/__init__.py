"""Operator jobs, benchmarks, and warmup."""

from audit_workbench.services.operator.auth import fetch_operator_benchmark_bearer_token
from audit_workbench.services.operator.benchmarks import (
    benchmark_command,
    create_benchmark_job,
    create_warmup_job,
)
from audit_workbench.services.operator.job_model import OperatorJob, operator_job_schema, utc_now
from audit_workbench.services.operator.jobs import (
    append_output,
    create_job,
    get_job,
    hydrate_operator_jobs_from_redis,
    list_jobs,
    run_command,
)
from audit_workbench.services.operator.reports import load_report
from audit_workbench.services.operator.requests import (
    BUILT_IN_FIXTURE_ROOT,
    BenchmarkRequest,
    OperatorRequestError,
    safe_model_identifier,
)

__all__ = [
    "BUILT_IN_FIXTURE_ROOT",
    "BenchmarkRequest",
    "OperatorJob",
    "OperatorRequestError",
    "append_output",
    "benchmark_command",
    "create_benchmark_job",
    "create_job",
    "create_warmup_job",
    "fetch_operator_benchmark_bearer_token",
    "get_job",
    "hydrate_operator_jobs_from_redis",
    "list_jobs",
    "load_report",
    "operator_job_schema",
    "run_command",
    "safe_model_identifier",
    "utc_now",
]
