"""Rate limit tests using limits MemoryStorage."""

from __future__ import annotations

import pytest
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

from audit_workbench.rules.logic_evaluator import evaluate_logic_rule
from audit_workbench.services import rate_limit as rate_limit_module
from audit_workbench.services.rate_limit import RateLimitExceeded, check_run_rate_limits
from audit_workbench.settings import Settings, clear_settings_cache


def test_evaluate_logic_rule_skips_missing_field():
    result = evaluate_logic_rule(
        {"id": "r1", "name": "Total", "body": "montant_total > 2000", "kind": "logic"},
        {},
    )
    assert result.status == "skipped"


@pytest.mark.asyncio
async def test_rate_limit_exceeded(monkeypatch):
    monkeypatch.setenv("AUDIT_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_RATE_LIMIT_RUNS_PER_WORKFLOW", "1")
    monkeypatch.setenv("AUDIT_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("AUDIT_EXTRACTION_CACHE_ENABLED", "false")
    clear_settings_cache()
    rate_limit_module.clear_rate_limiter_cache()
    rate_limit_module._storage = MemoryStorage()
    rate_limit_module._limiter = MovingWindowRateLimiter(rate_limit_module._storage)

    await check_run_rate_limits(workflow_id="wf-1", source="test", client_key=None)
    with pytest.raises(RateLimitExceeded):
        await check_run_rate_limits(workflow_id="wf-1", source="test", client_key=None)

    _ = Settings()
