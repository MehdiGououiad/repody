"""Hatchet stage bridge: run IDP extraction and validation for a ``repody-core`` case."""

import hashlib
import io
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from repody.app import execute, runs, workflows
from repody.app.errors import AppError
from repody.app.scope import own_workflow
from repody.infra import db
from repody.infra.models import Run, RunDocument
from repody.infra.storage import get_store
from repody.schemas.run import ExtractionMeta
from repody.schemas.stage import ArtifactRef, IdpStageInput, IdpStageOutput


def build_stage_output(run: Run) -> IdpStageOutput:
    """Convert a completed ``Run`` (with documents and fields loaded) to ``IdpStageOutput``."""
    if run.status != "done" or run.outcome is None:
        raise AppError(
            500,
            run.error or f"IDP run {run.id} finished with status {run.status}.",
        )

    type_counts = Counter(doc.document_type for doc in run.documents if doc.document_type)
    extracted_data: dict[str, Any] = {}
    flagged_fields: list[str] = []

    for doc in run.documents:
        if doc.document_type and type_counts[doc.document_type] == 1:
            doc_key = doc.document_type
        elif doc.document_type:
            doc_key = f"{doc.document_type}_{doc.position}"
        else:
            doc_key = doc.document_id

        extracted_data[doc_key] = {field.key: field.value for field in doc.fields}
        for field in doc.fields:
            if field.flagged:
                prefix = f"{doc.document_type}." if doc.document_type else ""
                flagged_fields.append(f"{prefix}{field.key}")

    pages_processed = sum(
        ExtractionMeta.model_validate(doc.extraction).pages_sent
        for doc in run.documents
        if doc.extraction
    )

    return IdpStageOutput(
        idp_run_id=run.id,
        outcome=run.outcome,
        extracted_data=extracted_data,
        flagged_fields=flagged_fields,
        pages_processed=pages_processed,
    )


async def _find_existing_run(
    client_key: str,
    idempotency_key: str,
) -> Run | None:
    async with db.session_factory() as session:
        return await session.scalar(
            select(Run)
            .where(Run.client_key == client_key, Run.idempotency_key == idempotency_key)
            .options(selectinload(Run.documents).selectinload(RunDocument.fields))
        )


async def _load_verified_uploads(artifacts: list[ArtifactRef]) -> list[runs.Upload]:
    store = get_store()
    uploads: list[runs.Upload] = []
    for artifact in artifacts:
        raw = await store.get(artifact.storage_key)
        digest = hashlib.sha256(raw).hexdigest().lower()
        if digest != artifact.sha256.lower():
            raise AppError(422, f"Artifact {artifact.artifact_id} SHA-256 mismatch.")
        file_name = artifact.storage_key.rsplit("/", 1)[-1] or artifact.artifact_id
        uploads.append(runs.Upload(file_name=file_name, file=io.BytesIO(raw), size=len(raw)))
    return uploads


async def execute_idp_stage(payload: IdpStageInput) -> IdpStageOutput:
    """Execute ``idp.extract_and_validate`` idempotently against immutable S3 artifacts."""
    account = payload.case.account_id
    client_key = f"core:{account or 'system'}"
    idempotency_key = f"core:{payload.case.case_id}:{payload.workflow_id}"

    existing = await _find_existing_run(client_key, idempotency_key)
    if existing is not None:
        if existing.status == "done":
            return build_stage_output(existing)
        if existing.status == "failed":
            raise AppError(500, existing.error or "IDP stage run failed.")
        run_id = existing.id
    else:
        source_artifacts = [
            a for a in (payload.artifacts or payload.case.artifacts) if a.kind == "source_document"
        ]
        if not source_artifacts:
            raise AppError(422, "IDP stage requires at least one source_document artifact.")

        async with db.session_factory() as session:
            wf = await workflows.find(session, payload.workflow_id, account=account)
            if wf is None:
                raise AppError(404, "Workflow not found.")
            own_workflow(wf, account)
            if wf.deployed_at is None:
                raise AppError(409, "Workflow is not deployed.")

        uploads = await _load_verified_uploads(source_artifacts)

        async with db.session_factory() as session:
            wf = await workflows.find(session, payload.workflow_id, account=account)
            if wf is None:
                raise AppError(404, "Workflow not found.")
            run_id, _ = await runs.create_run(
                session,
                wf,
                source="api",
                uploads=uploads,
                slots=[],
                client_key=client_key,
                idempotency_key=idempotency_key,
            )

    await execute.process_run(run_id)

    async with db.session_factory() as session:
        completed = await session.scalar(
            select(Run)
            .where(Run.id == run_id)
            .options(selectinload(Run.documents).selectinload(RunDocument.fields))
        )
    if completed is None:
        raise AppError(500, f"IDP run {run_id} disappeared after processing.")
    return build_stage_output(completed)
