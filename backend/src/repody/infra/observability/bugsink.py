"""Bugsink error tracking via Sentry-compatible SDK."""

from __future__ import annotations

import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration


def bugsink_enabled() -> bool:
    return bool(os.getenv("BUGSINK_DSN", "").strip())


def init_bugsink(service_name: str | None = None) -> None:
    dsn = os.getenv("BUGSINK_DSN", "").strip()
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("BUGSINK_ENVIRONMENT")
        or os.getenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "development"),
        release=os.getenv("BUGSINK_RELEASE"),
        server_name=service_name,
        send_default_pii=False,
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
    )
