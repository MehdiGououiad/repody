"""FastAPI entry point for ``repody-core``."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from repody_core.api import approvals, audit, cases, pipelines, platform
from repody_core.infra import db
from repody_core.schemas.errors import CoreError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await db.get_engine().dispose()


def create_app() -> FastAPI:
    """Create the ``repody-core`` FastAPI application."""
    app = FastAPI(title="Repody Core", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(CoreError)
    async def core_error(_request: Request, exc: CoreError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    for router in (
        platform.router,
        cases.router,
        pipelines.router,
        approvals.router,
        audit.router,
    ):
        app.include_router(router, prefix="/v1")
    return app


app = create_app()
