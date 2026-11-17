"""Runs and audits: start a run, poll it, list, read and export finished runs."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from repody.api.deps import AccountScope, OptionalUser, SessionDep, TokenDep, require
from repody.app import runs, workflows
from repody.app.scope import own_workflow, sees_workflow
from repody.infra.auth import User, api_key_matches, hash_api_key
from repody.infra.models import Workflow
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
from repody.settings import get_settings

router = APIRouter(tags=["runs"])
CSV = "text/csv; charset=utf-8"
UNAUTHORIZED = "Use the workflow API key or sign in with run permission."


def _upload(upload: UploadFile) -> runs.Upload:
    """The request's spooled file as is: it is streamed to storage, never read whole here.
    Starlette's multipart parser always counts the part's size."""
    return runs.Upload(
        file_name=upload.filename or "document", file=upload.file, size=upload.size or 0
    )


# The multipart body, documented by hand: the route reads it itself, after the caller is known.
START_RUN_BODY = {
    "required": True,
    "content": {
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "One file per workflow document.",
                    },
                    "documents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Per file, in order: the workflow document id or type.",
                    },
                    "definition": {
                        "type": "string",
                        "description": "Test runs only: an unsaved workflow definition (JSON).",
                    },
                },
            }
        }
    },
}


async def _caller(
    session: SessionDep, workflow_id: str, token: str | None, user: User | None
) -> tuple[Source, str, Workflow]:
    """Who starts the run, from the headers alone: the workflow API key (production) or a
    signed-in user with run:execute (test run). 401 for anyone else, whether or not the workflow
    exists; 404 for a workflow the caller cannot see."""
    wf = await workflows.find(session, workflow_id)
    if wf is not None and token and api_key_matches(token, wf.api_key_hash):
        return "api", hash_api_key(token)[:16], wf
    if user is None or not user.can("run:execute"):
        raise HTTPException(401, UNAUTHORIZED)
    if wf is None or not sees_workflow(wf, user.account):
        raise HTTPException(404, "Workflow not found.")  # another client's does not exist
    own_workflow(wf, user.account)
    return "test", user.subject, wf


@router.post(
    "/workflows/{workflow_id}/runs",
    status_code=202,
    openapi_extra={"requestBody": START_RUN_BODY},
    responses={
        400: {"description": "A malformed form, or more files or fields than allowed."},
        401: {"description": UNAUTHORIZED},
        402: {"description": "The workflow's account has not enough credits."},
        413: {"description": "The request is larger than AUDIT_MAX_REQUEST_BYTES."},
    },
)
async def start_run(
    request: Request,
    workflow_id: str,
    session: SessionDep,
    token: TokenDep,
    user: OptionalUser,
    idempotency_key: Annotated[
        str | None,
        Header(
            max_length=128,
            description="Retrying with the same key returns the run it started (202).",
        ),
    ] = None,
) -> RunCreated:
    """Start a run with the workflow API key (production) or as a signed-in user (test run).
    Poll ``GET /v1/runs/{run_id}`` until its status is done or failed. 402 when the workflow's
    account has not enough credits for the files' pages.

    The caller is checked before the body is read: without a valid key or session, nothing is
    uploaded (401)."""
    source, client_key, wf = await _caller(session, workflow_id, token, user)
    settings = get_settings()
    async with request.form(
        max_files=settings.max_upload_files,
        max_fields=settings.max_upload_files + 1,
        max_part_size=settings.max_json_bytes,
    ) as form:
        files = [f for f in form.getlist("files") if isinstance(f, UploadFile)]
        documents = [d for d in form.getlist("documents") if isinstance(d, str)]
        raw = form.get("definition")
        definition = None
        if source == "test" and isinstance(raw, str) and raw:
            try:
                definition = WorkflowDefinition.model_validate_json(raw)
            except ValidationError as error:
                raise RequestValidationError(error.errors(include_url=False)) from None
        return await runs.start_run(
            session,
            wf,
            source=source,
            uploads=[_upload(upload) for upload in files],
            slots=documents,
            client_key=client_key,
            definition=definition,
            idempotency_key=idempotency_key,
        )


async def require_run_reader(
    run_id: str, session: SessionDep, token: TokenDep, user: OptionalUser
) -> str | None:
    """Users with run:read (runs of their account), or the API key of the run's (not archived)
    workflow; the account the run is read as (None: any)."""
    if user is not None and user.can("run:read"):
        return user.account
    if token and api_key_matches(token, await runs.run_api_key_hash(session, run_id)):
        return None
    raise HTTPException(401, "Use the workflow API key or sign in.")


RunReaderScope = Annotated[str | None, Depends(require_run_reader)]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, session: SessionDep, account: RunReaderScope) -> RunState:
    """Status and live progress; the audit report once the run is done."""
    return await runs.run_state(session, run_id, account=account)


@router.get("/audits", dependencies=[require("run:read")])
async def list_audits(
    session: SessionDep, page: Annotated[AuditPage, Query()], account: AccountScope
) -> AuditList:
    return await runs.list_audits(session, page, account=account)


@router.get(
    "/audits/export.csv",
    dependencies=[require("run:read")],
    response_class=StreamingResponse,
    responses={200: {"content": {"text/csv": {}}, "description": "Every matching audit."}},
)
async def export_audits(
    session: SessionDep, audits: Annotated[AuditFilter, Query()], account: AccountScope
) -> StreamingResponse:
    return StreamingResponse(
        runs.export_audits(session, audits, account=account),
        media_type=CSV,
        headers={"Content-Disposition": 'attachment; filename="audits.csv"'},
    )


@router.get("/audits/{run_id}", dependencies=[require("run:read")])
async def get_audit(run_id: str, session: SessionDep, account: AccountScope) -> AuditDetail:
    return await runs.run_report(session, run_id, account=account)


@router.get(
    "/runs/{run_id}/documents/{document_id}/pages/{page}",
    dependencies=[require("run:read")],
    response_class=Response,
    responses={200: {"content": {"image/webp": {}}, "description": "The page, for the screen."}},
)
async def get_document_page(
    run_id: str,
    document_id: str,
    page: Annotated[int, Path(ge=1, le=999)],
    session: SessionDep,
    account: AccountScope,
) -> Response:
    """Page ``page`` (from 1) of a document uploaded to the run, rendered for the report."""
    image = await runs.document_page(session, run_id, document_id, page - 1, account=account)
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
async def export_audit(run_id: str, session: SessionDep, account: AccountScope) -> Response:
    return Response(
        await runs.export_report(session, run_id, account=account),
        media_type=CSV,
        headers={"Content-Disposition": f'attachment; filename="{run_id}.csv"'},
    )
