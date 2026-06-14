"""Optional Sentry / GlitchTip error reporting (Sentry-compatible DSN)."""

from __future__ import annotations

import logging
import os

import structlog

from audit_workbench.observability.glitchtip_logs import glitchtip_logs_enabled

log = structlog.get_logger(__name__)


def init_sentry(*, service_name: str | None = None, enable_logs: bool | None = None) -> bool:
    """Initialize sentry-sdk when SENTRY_DSN is set. Safe to call multiple times."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    if enable_logs is None:
        enable_logs = glitchtip_logs_enabled()

    environment = (
        os.getenv("SENTRY_ENVIRONMENT", "").strip()
        or os.getenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "").strip()
        or "development"
    )
    release = os.getenv("SENTRY_RELEASE", "").strip() or None

    integrations: list = [
        StarletteIntegration(),
        FastApiIntegration(),
    ]
    if enable_logs:
        integrations.append(
            LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR,
            )
        )

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        server_name=service_name,
        integrations=integrations,
        enable_logs=enable_logs,
        auto_session_tracking=False,
        traces_sample_rate=0.0,
        send_default_pii=False,
    )
    log.info(
        "sentry_initialized",
        event_domain="platform",
        environment=environment,
        service_name=service_name,
        enable_logs=enable_logs,
    )
    return True
