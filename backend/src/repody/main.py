"""The FastAPI application."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from repody.api import platform, runs, workflows
from repody.app import maintenance
from repody.app.errors import AppError
from repody.app.seed import seed
from repody.extraction import client
from repody.infra import db, observability, queue
from repody.infra.redis import close_redis
from repody.infra.storage import S3Store, get_store
from repody.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store = get_store()
    if isinstance(store, S3Store):
        await store.ensure_bucket()
    await queue.broker.startup()
    if get_settings().seed_on_startup:
        async with db.session_factory() as session:
            await seed(session)
            await session.commit()
    stop = asyncio.Event()
    upkeep = asyncio.create_task(maintenance.run_forever(stop))
    yield
    stop.set()
    await upkeep
    await queue.broker.shutdown()
    await client.close()
    await close_redis()
    await db.engine.dispose()


async def _app_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)


def create_app() -> FastAPI:
    observability.setup()
    app = FastAPI(title="Repody", version=version("repody"), lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, _app_error)
    for router in (workflows.router, runs.router, platform.router):
        app.include_router(router, prefix="/v1")
    return app


app = create_app()
