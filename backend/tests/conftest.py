import os

os.environ["AUDIT_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUDIT_RUN_JOBS_INLINE"] = os.environ.get("AUDIT_RUN_JOBS_INLINE", "false")
os.environ["AUDIT_RUN_EVENTS_ENABLED"] = os.environ.get("AUDIT_RUN_EVENTS_ENABLED", "false")
os.environ["AUDIT_EXTRACTION_CACHE_ENABLED"] = os.environ.get("AUDIT_EXTRACTION_CACHE_ENABLED", "false")
os.environ["AUDIT_AUTH_ENABLED"] = "false"
os.environ["AUDIT_RUN_MIGRATIONS_ON_STARTUP"] = "false"
os.environ["AUDIT_SEED_ON_STARTUP"] = "false"
os.environ["AUDIT_STORAGE_BACKEND"] = "local"
os.environ["AUDIT_LOCAL_STORAGE_PATH"] = os.path.join(os.path.dirname(__file__), ".storage")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from audit_workbench.db.base import Base
from audit_workbench.db.seed import seed_database
from audit_workbench.main import create_app
from audit_workbench.settings import get_settings
from tests.llm_mocks import disable_dmr_mock, enable_dmr_mock


@pytest.fixture(autouse=True)
def simulate_hatchet_dispatch(monkeypatch):
    """Exercise the Hatchet dispatch path; run worker logic in-process."""
    from tests.helpers.hatchet_sim import dispatch_audit_run_simulated

    monkeypatch.setattr(
        "audit_workbench.services.run_dispatch.dispatch_audit_run",
        dispatch_audit_run_simulated,
    )
    monkeypatch.setattr(
        "audit_workbench.api.runs.dispatch_audit_run",
        dispatch_audit_run_simulated,
    )


@pytest.fixture(autouse=True)
async def reset_inference_clients():
    """Avoid httpx pool / cached clients tied to a closed asyncio loop between tests."""
    yield
    from audit_workbench.inference.factory import get_inference_client
    from audit_workbench.inference.http_pool import close_async_http_client

    await close_async_http_client()
    get_inference_client.cache_clear()


@pytest.fixture
async def app():
    get_settings.cache_clear()
    engine = create_async_engine(
        os.environ["AUDIT_DATABASE_URL"],
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    import audit_workbench.db.base as db_base
    import audit_workbench.api.deps as deps

    db_base.engine = engine
    db_base.async_session_factory = session_factory
    deps.async_session_factory = session_factory

    application = create_app()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await seed_database(session)
        await session.commit()

    yield application
    from audit_workbench.hatchet.client import clear_hatchet_client
    from audit_workbench.services.run_dispatch import close_hatchet_client

    await close_hatchet_client()
    clear_hatchet_client()
    await engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_dmr(monkeypatch):
    """Mock Docker Model Runner for Repody VLM extraction and optional LLM validation."""
    router = enable_dmr_mock(monkeypatch)
    yield router
    disable_dmr_mock(router)


@pytest.fixture
def mock_ollama_llm(mock_dmr):
    return mock_dmr
