"""The FastAPI application."""

from contextlib import asynccontextmanager
from importlib.metadata import version

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from repody.api import access, admin, credits, platform, runs, workflows
from repody.app.errors import AppError
from repody.app.seed import seed
from repody.extraction import client
from repody.infra import db, keycloak_admin, observability
from repody.infra.storage import S3Store, get_store
from repody.settings import get_settings

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store = get_store()
    if isinstance(store, S3Store):
        await store.ensure_bucket()
    if get_settings().seed_on_startup:
        async with db.session_factory() as session:
            await seed(session)
            await session.commit()
    yield
    await client.close()
    if keycloak_admin.enabled():
        await keycloak_admin.keycloak_admin().close()
    await db.engine.dispose()


class BodyLimit:
    """413 for a request body over its limit: AUDIT_MAX_REQUEST_BYTES for a multipart upload,
    AUDIT_MAX_JSON_BYTES for anything else. Counted as the body arrives, so a body without a
    Content-Length (chunked) or with a false one is limited too; a declared length over the
    limit is refused before anything is read."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        settings = get_settings()
        multipart = headers.get("content-type", "").startswith("multipart/form-data")
        limit = settings.max_request_bytes if multipart else settings.max_json_bytes
        detail = f"The request body is larger than {limit} bytes."
        length = headers.get("content-length", "")
        if length.isdigit() and int(length) > limit:
            log.warning("request_too_large", path=scope.get("path"), bytes=int(length))
            await JSONResponse({"detail": detail}, status_code=413)(scope, receive, send)
            return
        received = 0

        async def counted() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    log.warning("request_too_large", path=scope.get("path"), bytes=received)
                    raise HTTPException(413, detail)
            return message

        await self.app(scope, counted, send)


def create_app() -> FastAPI:
    observability.setup()
    settings = get_settings()
    app = FastAPI(title="Repody", version=version("repody"), lifespan=lifespan)
    app.add_middleware(BodyLimit)
    if settings.cors_origins:
        # Only for browser apps on other origins; requests carry a bearer token, no cookies.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.exception_handler(AppError)
    async def app_error(_request: Request, exc: AppError) -> JSONResponse:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)

    for router in (
        workflows.router,
        runs.router,
        platform.router,
        credits.router,
        admin.router,
        access.router,
    ):
        app.include_router(router, prefix="/v1")
    return app


app = create_app()
