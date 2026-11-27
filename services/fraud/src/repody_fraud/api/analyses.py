"""Standalone and pipeline-accessible Fraud Shield HTTP routes."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from repody_fraud.api.deps import ServiceDep, require
from repody_fraud.infra.auth import FraudUser
from repody_fraud.schemas.analyses import AnalysisResponse
from repody_fraud.schemas.errors import ValidationError

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", status_code=201)
async def create_analysis(
    service: ServiceDep,
    user: Annotated[FraudUser, require("fraud:write")],
    files: Annotated[list[UploadFile], File(default_factory=list)],
    extracted_data: Annotated[str | None, Form()] = None,
    case_id: Annotated[str | None, Form()] = None,
) -> AnalysisResponse:
    """Analyze uploaded PDF/image documents and/or structured fields for fraud."""
    parsed_data: dict[str, Any] | None = None
    if extracted_data:
        try:
            loaded = json.loads(extracted_data)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, f"extracted_data must be valid JSON: {exc}") from None
        if not isinstance(loaded, dict):
            raise ValidationError("extracted_data JSON must be an object.")
        parsed_data = loaded

    blobs: list[tuple[str, bytes, str]] = []
    for item in files:
        raw = await item.read()
        mime = item.content_type or "application/octet-stream"
        blobs.append((item.filename or "document", raw, mime))

    return await service.run_standalone_analysis(
        files=blobs,
        extracted_data=parsed_data,
        account_id=user.account,
        case_id=case_id,
    )


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    service: ServiceDep,
    user: Annotated[FraudUser, require("fraud:read")],
) -> AnalysisResponse:
    """Fetch an analysis report scoped to the caller's account."""
    return await service.get_analysis(analysis_id, account_id=user.account)


@router.get(
    "/{analysis_id}/artifacts/{artifact_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "Forensic evidence PNG."}},
)
async def get_artifact(
    analysis_id: str,
    artifact_id: str,
    service: ServiceDep,
    user: Annotated[FraudUser, require("fraud:read")],
) -> Response:
    """Download a forensic heatmap or PDF revision diff artifact."""
    data, mime_type = await service.get_artifact_bytes(
        analysis_id, artifact_id, account_id=user.account
    )
    return Response(
        data,
        media_type=mime_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )
