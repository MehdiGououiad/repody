"""OpenAPI customization: security schemes and shared metadata."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

BEARER_AUTH_SCHEME = "bearerAuth"


def install_openapi(app: FastAPI) -> None:
    """Attach a cached OpenAPI schema with documented security schemes."""

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        components = openapi_schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes[BEARER_AUTH_SCHEME] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API token",
            "description": (
                "Keycloak access token (`Authorization: Bearer <jwt>`) for UI users, or a "
                "per-workflow API key for run endpoints."
            ),
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
