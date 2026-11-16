"""The FastAPI application."""

from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from repody.api import platform, runs, workflows
from repody.app.errors import AppError
from repody.app.seed import seed
from repody.extraction import client
from repody.infra import db, observability
from repody.infra.storage import S3Store, get_store
from repody.settings import get_settings


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
    await db.engine.dispose()


def create_app() -> FastAPI:
    observability.setup()
    settings = get_settings()
    app = FastAPI(title="Repody", version=version("repody"), lifespan=lifespan)
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

    for router in (workflows.router, runs.router, platform.router):
        app.include_router(router, prefix="/v1")
    return app


app = create_app()
