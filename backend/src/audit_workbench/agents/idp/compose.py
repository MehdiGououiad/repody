"""Compose IDP steps into IdpOutcome (ports injected; no DB/HTTP here)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from audit_workbench.agents.idp.contracts import (
    DocumentExtraction,
    DocumentSpec,
    ExtractionOutput,
    IdpInput,
    IdpOutcome,
    StoredDocument,
    ValidationOutput,
)
from audit_workbench.extraction.modes import (
    document_has_schema_fields,
    extraction_is_needed,
)
from audit_workbench.runtime.contracts.result import AppError, ErrorCode, Result


@dataclass(frozen=True, slots=True)
class ExtractionJob:
    document_id: str
    spec: DocumentSpec
    stored: StoredDocument


def needs_extraction(spec: DocumentSpec, stored: StoredDocument | None) -> bool:
    """True when the pipeline should invoke extraction for this document slot."""
    return extraction_is_needed(
        has_file=stored is not None,
        has_schema_fields=document_has_schema_fields(spec),
        markdown_extraction=bool(spec.markdown_extraction),
    )


def build_extraction_plan(
    documents: tuple[DocumentSpec, ...],
    stored_by_id: dict[str, StoredDocument],
) -> tuple[ExtractionJob, ...]:
    jobs: list[ExtractionJob] = []
    for spec in documents:
        stored = stored_by_id.get(spec.id)
        if needs_extraction(spec, stored) and stored is not None:
            jobs.append(
                ExtractionJob(document_id=spec.id, spec=spec, stored=stored)
            )
    return tuple(jobs)


FetchBytes = Callable[[str], Awaitable[bytes]]
ExtractOne = Callable[
    [DocumentSpec, StoredDocument, bytes],
    Awaitable[Result[DocumentExtraction]],
]
ValidatePort = Callable[[ExtractionOutput], Awaitable[ValidationOutput]]
OnExtractStart = Callable[[ExtractionJob, int, int], Awaitable[None]]
OnExtractDone = Callable[[ExtractionJob, Result[DocumentExtraction]], Awaitable[None]]


async def compose_idp(
    inp: IdpInput,
    *,
    fetch_bytes: FetchBytes,
    extract_one: ExtractOne,
    validate: ValidatePort,
    on_extract_start: OnExtractStart | None = None,
    on_extract_done: OnExtractDone | None = None,
) -> Result[IdpOutcome]:
    """Plan → extract → validate. Soft per-document failures become IdpOutcome.errors."""
    stored_by_id = {d.document_id: d for d in inp.documents}
    jobs = build_extraction_plan(inp.workflow.documents, stored_by_id)

    extractions: list[DocumentExtraction] = []
    errors: list[AppError] = []

    for index, job in enumerate(jobs):
        if on_extract_start is not None:
            await on_extract_start(job, index, len(jobs))

        try:
            blob = await fetch_bytes(job.stored.storage_key)
        except Exception as exc:  # noqa: BLE001
            failed = Result.fail(
                AppError(
                    code=ErrorCode.INFRA,
                    message="Failed to load document bytes",
                    document_id=job.document_id,
                    cause=repr(exc),
                )
            )
            if failed.error is not None:
                errors.append(failed.error)
            if on_extract_done is not None:
                await on_extract_done(job, failed)
            continue

        result = await extract_one(job.spec, job.stored, blob)
        if on_extract_done is not None:
            await on_extract_done(job, result)
        if not result.is_ok:
            if result.error is not None:
                errors.append(
                    AppError(
                        code=result.error.code,
                        message=result.error.message,
                        document_id=job.document_id,
                        cause=result.error.cause,
                    )
                )
            continue
        if result.value is not None:
            extractions.append(result.value)

    extraction_out = ExtractionOutput(by_document=tuple(extractions))
    validation_out = await validate(extraction_out)

    return Result.ok(
        IdpOutcome(
            run_id=inp.run_id,
            workflow_id=inp.workflow.workflow_id,
            extraction=extraction_out,
            validation=validation_out,
            errors=tuple(errors),
        )
    )
