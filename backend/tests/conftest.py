import os

from tests.helpers.db import DEFAULT_TEST_DATABASE_URL

# Test defaults — production uses Postgres + Alembic; live tests use the docker stack.
_db_url = os.environ.get("AUDIT_DATABASE_URL", "")
if not _db_url:
    os.environ["AUDIT_DATABASE_URL"] = DEFAULT_TEST_DATABASE_URL
os.environ["AUDIT_RUN_EVENTS_ENABLED"] = os.environ.get("AUDIT_RUN_EVENTS_ENABLED", "false")
os.environ["AUDIT_EXTRACTION_CACHE_ENABLED"] = os.environ.get(
    "AUDIT_EXTRACTION_CACHE_ENABLED", "false"
)
os.environ["AUDIT_OIDC_ENABLED"] = "false"
os.environ["AUDIT_RUN_MIGRATIONS_ON_STARTUP"] = "false"
os.environ["AUDIT_SEED_ON_STARTUP"] = "false"
os.environ["AUDIT_STORAGE_BACKEND"] = "local"
os.environ["AUDIT_LOCAL_STORAGE_PATH"] = os.path.join(os.path.dirname(__file__), ".storage")
os.environ["AUDIT_GPU_LIVE_PROBE"] = "false"
os.environ["AUDIT_HEALTHZ_PROBE_INFERENCE"] = "false"
os.environ["AUDIT_INFERENCE_MODE"] = "docker_model_runner"
os.environ["AUDIT_DOCKER_MODEL_RUNNER_BASE_URL"] = "http://model-runner-mock.test/v1"
os.environ["AUDIT_TEST_POLL_INTERVAL_MS"] = "50"
os.environ["AUDIT_RATE_LIMIT_ENABLED"] = "false"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from unittest.mock import AsyncMock

from audit_workbench.main import create_app
from audit_workbench.settings import clear_settings_cache, get_settings
from tests.helpers.db import (
    bind_test_database,
    configure_test_database_url,
    create_test_engine,
    ensure_postgres_database,
    patch_session_factory,
    reset_test_database,
    upgrade_database_to_head,
)
from tests.llm_mocks import disable_dmr_mock, enable_dmr_mock

_session_dmr_router: dict[str, object] = {"router": None}


@pytest.fixture(autouse=True)
def fresh_settings():
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture(autouse=True)
def mock_redis_readiness_for_inprocess_tests(monkeypatch, request):
    """Unit/e2e ASGI tests have no Redis; readiness still validates the probe path."""
    if request.node.get_closest_marker("live"):
        return
    monkeypatch.setattr(
        "audit_workbench.services.platform_health.ping_redis",
        AsyncMock(return_value=True),
    )


@pytest.fixture
async def live_client(request):
    """HTTP client against a running docker/k8s stack (Taskiq workers)."""
    if request.node.get_closest_marker("live") is None:
        pytest.skip("live_client fixture requires @pytest.mark.live")
    if os.environ.get("E2E_STACK") != "1" and not os.environ.get("E2E_API_URL"):
        pytest.skip("Set E2E_STACK=1 or E2E_API_URL for live API tests")
    from audit_workbench.integration.live_stack import create_live_async_client

    async with create_live_async_client() as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def test_session_factory():
    """One migrated Postgres database per test session (Alembic, same as prod)."""
    database_url = configure_test_database_url()
    await ensure_postgres_database(database_url)
    upgrade_database_to_head(database_url)

    engine = create_test_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    bind_test_database(engine, session_factory)

    yield session_factory

    await engine.dispose()
    get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session")
async def app(test_session_factory):
    """Real ASGI app against migrated Postgres (UI-identical routes)."""
    os.environ["AUDIT_OIDC_ENABLED"] = "false"
    os.environ["AUDIT_OIDC_AUDIENCE"] = ""
    get_settings.cache_clear()
    router = enable_dmr_mock(monkeypatch=None)
    _session_dmr_router["router"] = router

    application = create_app()

    yield application

    from audit_workbench.services.run_dispatch import close_taskiq_brokers
    from audit_workbench.taskiq.broker import clear_broker_cache
    from audit_workbench.taskiq.tasks import clear_task_registry

    await close_taskiq_brokers()
    clear_broker_cache()
    clear_task_registry()
    disable_dmr_mock(router)
    _session_dmr_router["router"] = None
    get_settings.cache_clear()


@pytest.fixture
async def postgres_session(monkeypatch, test_session_factory):
    """Async session on migrated Postgres; DB truncated + seeded before each use."""
    await reset_test_database(test_session_factory)
    patch_session_factory(monkeypatch, test_session_factory)
    async with test_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def drain_background_tasks():
    """Let fire-and-forget Taskiq dispatch tasks finish before the next test."""
    yield
    from audit_workbench.services.dispatch_outbox import drain_dispatch_tasks

    await drain_dispatch_tasks()


@pytest.fixture(autouse=True)
async def reset_inference_clients():
    """Drop cached httpx clients between tests (session loop keeps the same event loop)."""
    yield
    from audit_workbench.inference.factory import get_inference_client
    from audit_workbench.inference.openai_compat import close_openai_clients

    await close_openai_clients()
    get_inference_client.cache_clear()


@pytest.fixture
async def client(app, test_session_factory, monkeypatch):
    await reset_test_database(test_session_factory)
    patch_session_factory(monkeypatch, test_session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_dmr(app):
    """Session Model Runner mock (real API routes, stubbed inference HTTP)."""
    return _session_dmr_router["router"]


@pytest.fixture
def mock_ollama_llm(mock_dmr):
    return mock_dmr
