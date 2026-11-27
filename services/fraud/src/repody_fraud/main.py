"""FastAPI entry point for ``repody-fraud``."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from repody_fraud.api import analyses, health
from repody_fraud.infra import db
from repody_fraud.schemas.errors import FraudError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await db.get_engine().dispose()


def create_app() -> FastAPI:
    """Create the standalone Fraud Shield FastAPI application."""
    app = FastAPI(title="Repody Fraud Shield", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(FraudError)
    async def fraud_error(_request: Request, exc: FraudError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    for router in (health.router, analyses.router):
        app.include_router(router, prefix="/v1")
    return app


app = create_app()
