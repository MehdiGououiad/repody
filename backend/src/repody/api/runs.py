from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sse_starlette import EventSourceResponse

from repody.api.deps import BearerDep, OptionalUser, SessionDep, require, token_of
from repody.app import progress, runs, workflows
from repody.infra.auth import api_key_matches, hash_api_key
from repody.schemas.run import AuditDetail, AuditList, RunCreated, RunState
from repody.schemas.workflow import WorkflowDefinition
from repody.settings import get_settings

router = APIRouter(tags=["runs"])


async def _read(upload: UploadFile) -> runs.Upload:
    limit = get_settings().max_upload_bytes
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"{upload.filename} is larger than {limit} bytes.")
    if not data:
        raise HTTPException(422, f"{upload.filename} is empty.")
    return runs.Upload(file_name=upload.filename or "document", data=data)


@router.post("/workflows/{workflow_id}/runs", status_code=202)
async def start_run(
    workflow_id: str,
    session: SessionDep,
    credentials: BearerDep,
    user: OptionalUser,
    files: Annotated[list[UploadFile], File(description="One file per workflow document.")] = [],  # noqa: B006
    documents: Annotated[
        list[str], Form(description="Per file, in order: the workflow document id or type.")
    ] = [],  # noqa: B006
    definition: Annotated[
        str | None, Form(description="Test runs only: an unsaved workflow definition (JSON).")
    ] = None,
) -> RunCreated:
    """Start a run with the workflow API key (production) or as a signed-in user (test run)."""
    wf = await workflows.load(session, workflow_id)
    token = token_of(credentials)
    if token and api_key_matches(token, wf.api_key_hash):
        source, client_key = "api", hash_api_key(token)[:16]
    elif user is not None and user.can("run:execute"):
        source, client_key = "test", user.subject
    else:
        raise HTTPException(401, "Use the workflow API key or sign in with run permission.")
    draft = None
    if definition and source == "test":
        try:
            draft = WorkflowDefinition.model_validate_json(definition)
        except ValidationError as exc:
            raise HTTPException(422, f"Invalid definition: {exc.errors()[0]['msg']}") from exc
    return await runs.start_run(
        session,
        wf,
        source=source,
        uploads=[await _read(upload) for upload in files],
        slots=documents,
        client_key=client_key,
        definition=draft,
    )


async def require_run_reader(
    run_id: str, session: SessionDep, credentials: BearerDep, user: OptionalUser
) -> None:
    """Users with run:read, or the API key of the run's workflow."""
    if user is not None and user.can("run:read"):
        return
    token = token_of(credentials)
    if token and api_key_matches(token, await runs.run_api_key_hash(session, run_id)):
        return
    raise HTTPException(401, "Use the workflow API key or sign in.")


RunReader = Depends(require_run_reader)


@router.get("/runs/{run_id}", dependencies=[RunReader])
async def get_run(run_id: str, session: SessionDep) -> RunState:
    """Status and live progress; the audit report once the run is done."""
    return await runs.run_state(session, run_id)


@router.get(
    "/runs/{run_id}/events",
    dependencies=[RunReader],
    responses={200: {"content": {"text/event-stream": {}}, "description": "Progress events"}},
)
async def run_events(run_id: str, session: SessionDep) -> EventSourceResponse:
    """Server-Sent Events: the current state first, then each progress change until done."""
    state = await runs.run_state(session, run_id)
    await session.close()

    async def events():
        yield {
            "data": json.dumps(
                {"progress": state.progress.model_dump() if state.progress else None}
            )
        }
        if state.status in ("done", "failed"):
            yield {"data": json.dumps({"terminal": True, "status": state.status})}
            return
        async for message in progress.subscribe(run_id):
            yield {"data": message}

    return EventSourceResponse(events(), ping=15)


@router.get("/audits", dependencies=[require("run:read")])
async def list_audits(session: SessionDep, limit: int = 50, offset: int = 0) -> AuditList:
    return await runs.list_audits(session, limit=limit, offset=offset)


@router.get("/audits/{run_id}", dependencies=[require("run:read")])
async def get_audit(run_id: str, session: SessionDep) -> AuditDetail:
    return await runs.run_report(session, run_id)
