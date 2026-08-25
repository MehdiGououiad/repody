"""NuExtract platform REST client (structured extraction).

Official API: https://nuextract.ai/doc / https://documentation.nuextract.ai/

Auth: ``Authorization: Bearer <api_key>``
Jobs are async: submit → stream ``/api/jobs/{jobId}/stream`` (SSE) until event ``result``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

DEFAULT_BASE_URL = "https://nuextract.ai"
TMP_PROJECT_NAME = "repody_tmp_project"
SSE_RESULT_EVENT = "result"


class NuExtractCloudError(RuntimeError):
    """Raised when the NuExtract platform API rejects or fails a request."""


@dataclass(frozen=True)
class NuExtractCloudConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 180.0
    project_id: str | None = None


@dataclass(frozen=True)
class StructuredExtractionOutput:
    """Parsed structured-extraction job payload."""

    result: dict[str, Any]
    raw_model_output: str
    thinking_trace: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    project_id: str
    job_id: str


def parse_sse_string(raw: str) -> list[dict[str, str]]:
    """Parse an SSE body into message dicts (``event``, ``data``, …)."""
    messages: list[dict[str, str]] = []
    msg: dict[str, str] = {}
    data_buf: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            if data_buf or msg:
                msg["data"] = "\n".join(data_buf)
                messages.append(msg)
                msg, data_buf = {}, []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value.lstrip(" ")
        if field == "data":
            data_buf.append(value)
        else:
            msg[field] = value
    if data_buf or msg:
        msg["data"] = "\n".join(data_buf)
        messages.append(msg)
    return messages


def _filename_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if mime == "application/pdf":
        return "document.pdf"
    if mime in {"image/jpeg", "image/jpg"}:
        return "document.jpg"
    if mime == "image/png":
        return "document.png"
    if mime == "image/webp":
        return "document.webp"
    if mime == "image/gif":
        return "document.gif"
    return "document.bin"


def _raise_for_api_error(response: httpx.Response, *, action: str) -> None:
    if response.is_success:
        return
    detail = response.text
    try:
        body = response.json()
        detail = body.get("message") or body.get("code") or detail
    except Exception:
        pass
    raise NuExtractCloudError(f"NuExtract cloud {action} failed ({response.status_code}): {detail}")


def _parse_stream_result(raw: str) -> dict[str, Any]:
    messages = parse_sse_string(raw)
    if not messages:
        raise NuExtractCloudError("NuExtract cloud job stream was empty.")
    last = messages[-1]
    event = last.get("event") or ""
    try:
        payload = json.loads(last.get("data") or "{}")
    except json.JSONDecodeError as exc:
        raise NuExtractCloudError(f"NuExtract cloud job stream data was not JSON: {exc}") from exc

    status = str(payload.get("status") or "").lower()
    if status == "failed" or payload.get("errorCode") or payload.get("errorMessage"):
        code = payload.get("errorCode") or "failed"
        message = payload.get("errorMessage") or payload.get("message") or payload
        raise NuExtractCloudError(f"NuExtract cloud job failed ({code}): {message}")

    if event != SSE_RESULT_EVENT:
        raise NuExtractCloudError(
            f"NuExtract cloud job did not complete (event={event!r}): {payload}"
        )
    output_data = payload.get("outputData")
    if output_data is None:
        raise NuExtractCloudError(f"NuExtract cloud job completed without outputData: {payload}")
    if isinstance(output_data, str):
        try:
            return json.loads(output_data)
        except json.JSONDecodeError as exc:
            raise NuExtractCloudError(f"NuExtract cloud outputData was not JSON: {exc}") from exc
    if isinstance(output_data, dict):
        return output_data
    raise NuExtractCloudError(
        f"NuExtract cloud outputData has unexpected type: {type(output_data).__name__}"
    )


def _require_api_key(config: NuExtractCloudConfig) -> None:
    if not (config.api_key or "").strip():
        raise NuExtractCloudError(
            "NuExtract cloud API key is missing. Set AUDIT_NUEXTRACT_CLOUD_API_KEY."
        )


def _http_client(config: NuExtractCloudConfig) -> httpx.AsyncClient:
    _require_api_key(config)
    return httpx.AsyncClient(
        base_url=config.base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {config.api_key.strip()}"},
        timeout=httpx.Timeout(config.timeout_seconds),
    )


async def list_projects(config: NuExtractCloudConfig) -> list[dict[str, Any]]:
    async with _http_client(config) as client:
        response = await client.get("/api/structured-extraction")
        _raise_for_api_error(response, action="list projects")
        data = response.json()
        return data if isinstance(data, list) else []


async def create_project(
    config: NuExtractCloudConfig,
    *,
    template: dict[str, Any],
    instructions: str = "",
    name: str = TMP_PROJECT_NAME,
    description: str = "",
) -> str:
    body = {
        "name": name,
        "description": description,
        "template": template,
        "instructions": instructions or "",
    }
    async with _http_client(config) as client:
        response = await client.post("/api/structured-extraction", json=body)
        _raise_for_api_error(response, action="create project")
        project_id = response.json().get("id")
        if not project_id:
            raise NuExtractCloudError("NuExtract cloud create project returned no id.")
        return str(project_id)


async def update_project(
    config: NuExtractCloudConfig,
    project_id: str,
    *,
    template: dict[str, Any],
    instructions: str = "",
    name: str | None = None,
    description: str | None = None,
) -> None:
    body: dict[str, Any] = {
        "template": template,
        "instructions": instructions or "",
    }
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    async with _http_client(config) as client:
        response = await client.patch(
            f"/api/structured-extraction/{project_id}",
            json=body,
        )
        _raise_for_api_error(response, action="update project")


async def delete_project(config: NuExtractCloudConfig, project_id: str) -> None:
    async with _http_client(config) as client:
        response = await client.delete(f"/api/structured-extraction/{project_id}")
        if response.status_code == 404:
            return
        _raise_for_api_error(response, action="delete project")


async def submit_file_job(
    config: NuExtractCloudConfig,
    project_id: str,
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> str:
    files = {"file": (filename, file_bytes, mime_type or "application/octet-stream")}
    async with _http_client(config) as client:
        response = await client.post(
            f"/api/structured-extraction/{project_id}/jobs",
            files=files,
        )
        _raise_for_api_error(response, action="submit file job")
        job_id = response.json().get("jobId") or response.json().get("job_id")
        if not job_id:
            raise NuExtractCloudError("NuExtract cloud submit job returned no jobId.")
        return str(job_id)


async def submit_text_job(config: NuExtractCloudConfig, project_id: str, text: str) -> str:
    async with _http_client(config) as client:
        response = await client.post(
            f"/api/structured-extraction/{project_id}/jobs",
            content=text.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )
        _raise_for_api_error(response, action="submit text job")
        job_id = response.json().get("jobId") or response.json().get("job_id")
        if not job_id:
            raise NuExtractCloudError("NuExtract cloud submit job returned no jobId.")
        return str(job_id)


async def stream_job_result(config: NuExtractCloudConfig, job_id: str) -> dict[str, Any]:
    async with (
        _http_client(config) as client,
        client.stream(
            "GET",
            f"/api/jobs/{job_id}/stream",
            headers={"Accept": "text/event-stream"},
        ) as response,
    ):
        if not response.is_success:
            body = (await response.aread()).decode("utf-8", errors="replace")
            detail = body
            try:
                parsed = json.loads(body)
                detail = parsed.get("message") or parsed.get("code") or body
            except Exception:
                pass
            raise NuExtractCloudError(
                f"NuExtract cloud stream failed ({response.status_code}): {detail}"
            )
        chunks: list[str] = []
        async for part in response.aiter_text():
            chunks.append(part)
        return _parse_stream_result("".join(chunks))


async def extract_structured(
    config: NuExtractCloudConfig,
    *,
    template: dict[str, Any],
    file_bytes: bytes | None = None,
    mime_type: str = "application/octet-stream",
    filename: str | None = None,
    text: str | None = None,
    instructions: str = "",
    project_id: str | None = None,
) -> StructuredExtractionOutput:
    """Run structured extraction via temp project (or a configured project id)."""
    if bool(file_bytes is None) == bool(text is None):
        raise NuExtractCloudError(
            "Provide exactly one of file_bytes or text for NuExtract cloud extraction."
        )

    configured = (project_id or config.project_id or "").strip() or None
    ephemeral = configured is None
    active_project = configured

    if ephemeral:
        active_project = await create_project(
            config,
            template=template,
            instructions=instructions,
        )
    else:
        await update_project(
            config,
            active_project,
            template=template,
            instructions=instructions,
        )

    assert active_project is not None
    try:
        if file_bytes is not None:
            job_id = await submit_file_job(
                config,
                active_project,
                file_bytes=file_bytes,
                filename=filename or _filename_for_mime(mime_type),
                mime_type=mime_type,
            )
        else:
            job_id = await submit_text_job(config, active_project, text or "")
        payload = await stream_job_result(config, job_id)
    finally:
        if ephemeral:
            try:
                await delete_project(config, active_project)
            except Exception as exc:
                log.warning(
                    "nuextract_cloud_tmp_project_delete_failed",
                    project_id=active_project,
                    error=repr(exc),
                )

    result = payload.get("result")
    if not isinstance(result, dict):
        raise NuExtractCloudError(f"NuExtract cloud result missing or invalid: {payload!r}")
    return StructuredExtractionOutput(
        result=result,
        raw_model_output=str(
            payload.get("rawModelOutput") or payload.get("raw_model_output") or ""
        ),
        thinking_trace=payload.get("thinkingTrace") or payload.get("thinking_trace"),
        input_tokens=int(payload.get("inputTokens") or payload.get("input_tokens") or 0),
        output_tokens=int(payload.get("outputTokens") or payload.get("output_tokens") or 0),
        total_tokens=int(payload.get("totalTokens") or payload.get("total_tokens") or 0),
        project_id=active_project,
        job_id=job_id,
    )
