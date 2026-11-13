"""Runs and audits: start a run, poll it, list, read and export finished runs."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import Json

from repody.api.deps import CREDITS, OptionalUser, SessionDep, TokenDep, require
from repody.app import runs, workflows
from repody.infra.auth import api_key_matches, hash_api_key
from repody.schemas.run import (
    AuditDetail,
    AuditFilter,
    AuditList,
    AuditPage,
    RunCreated,
    RunState,
    Source,
)
from repody.schemas.workflow import WorkflowDefinition

router = APIRouter(tags=["runs"])
CSV = "text/csv; charset=utf-8"
UNAUTHORIZED = "Use the workflow API key or sign in with run permission."


def _upload(upload: UploadFile) -> runs.Upload:
    """The request's spooled file as is: it is streamed to storage, never read whole here.
    Starlette's multipart parser always counts the part's size."""
    return runs.Upload(
        file_name=upload.filename or "document", file=upload.file, size=upload.size or 0
    )


@router.post("/workflows/{workflow_id}/runs", status_code=202)
async def start_run(
    workflow_id: str,
    session: SessionDep,
    token: TokenDep,
    user: OptionalUser,
    files: Annotated[list[UploadFile], File(description="One file per workflow document.")] = [],  # noqa: B006
    documents: Annotated[
        list[str], Form(description="Per file, in order: the workflow document id or type.")
    ] = [],  # noqa: B006
    definition: Annotated[
        Json[WorkflowDefinition] | None,
        Form(description="Test runs only: an unsaved workflow definition (JSON)."),
    ] = None,
) -> RunCreated:
    """Start a run with the workflow API key (production) or as a signed-in user (test run).
    Poll ``GET /v1/runs/{run_id}`` until its status is done or failed.

    A caller that is neither gets 401 whether or not the workflow exists."""
    if user is not None and user.visitor:
        raise HTTPException(402, CREDITS)  # the playground runs nothing
    wf = await workflows.find(session, workflow_id)
    caller: tuple[Source, str] | None = None
    if wf is not None and token and api_key_matches(token, wf.api_key_hash):
        caller = ("api", hash_api_key(token)[:16])
    elif user is not None and user.can("run:execute"):
        caller = ("test", user.subject)
    if caller is None:
        raise HTTPException(401, UNAUTHORIZED)
    if wf is None:
        raise HTTPException(404, "Workflow not found.")
    source, client_key = caller
    return await runs.start_run(
        session,
        wf,
        source=source,
        uploads=[_upload(upload) for upload in files],
        slots=documents,
        client_key=client_key,
        definition=definition if source == "test" else None,
    )


async def require_run_reader(
    run_id: str, session: SessionDep, token: TokenDep, user: OptionalUser
) -> None:
    """Users with run:read, or the API key of the run's (not archived) workflow."""
    if user is not None and user.can("run:read"):
        return
    if token and api_key_matches(token, await runs.run_api_key_hash(session, run_id)):
        return
    raise HTTPException(401, "Use the workflow API key or sign in.")


RunReader = Depends(require_run_reader)


@router.get("/runs/{run_id}", dependencies=[RunReader])
async def get_run(run_id: str, session: SessionDep) -> RunState:
    """Status and live progress (with the queue position while queued); the audit report once
    the run is done."""
    return await runs.run_state(session, run_id)


@router.get("/audits", dependencies=[require("run:read")])
async def list_audits(session: SessionDep, page: Annotated[AuditPage, Query()]) -> AuditList:
    return await runs.list_audits(session, page)


@router.get(
    "/audits/export.csv",
    dependencies=[require("run:read")],
    response_class=StreamingResponse,
    responses={200: {"content": {"text/csv": {}}, "description": "Every matching audit."}},
)
async def export_audits(
    session: SessionDep, audits: Annotated[AuditFilter, Query()]
) -> StreamingResponse:
    return StreamingResponse(
        runs.export_audits(session, audits),
        media_type=CSV,
        headers={"Content-Disposition": 'attachment; filename="audits.csv"'},
    )


@router.get("/audits/{run_id}", dependencies=[require("run:read")])
async def get_audit(run_id: str, session: SessionDep) -> AuditDetail:
    return await runs.run_report(session, run_id)


@router.get(
    "/runs/{run_id}/documents/{document_id}/pages/{page}",
    dependencies=[require("run:read")],
    response_class=Response,
    responses={200: {"content": {"image/webp": {}}, "description": "The page, for the screen."}},
)
async def get_document_page(
    run_id: str, document_id: str, page: Annotated[int, Path(ge=1, le=999)], session: SessionDep
) -> Response:
    """Page ``page`` (from 1) of a document uploaded to the run, rendered for the report."""
    image = await runs.document_page(session, run_id, document_id, page - 1)
    # A run's files never change: the browser keeps the page for the session.
    return Response(
        image, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"}
    )


@router.get(
    "/audits/{run_id}/export.csv",
    dependencies=[require("run:read")],
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "Fields and rule results."}},
)
async def export_audit(run_id: str, session: SessionDep) -> Response:
    return Response(
        await runs.export_report(session, run_id),
        media_type=CSV,
        headers={"Content-Disposition": f'attachment; filename="{run_id}.csv"'},
    )
