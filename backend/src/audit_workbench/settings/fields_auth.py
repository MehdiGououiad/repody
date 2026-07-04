from __future__ import annotations

import json

from pydantic import AliasChoices, Field


class AuthSettingsFields:
    oidc_enabled: bool = Field(
        default=False,
        description="Require Keycloak JWT on management endpoints (disable for local pytest).",
    )
    oidc_issuer: str | None = Field(
        default=None,
        description="OIDC issuer URL, e.g. http://keycloak:8080/realms/repody",
    )
    oidc_issuer_aliases_env: str = Field(
        default="",
        validation_alias=AliasChoices("OIDC_ISSUER_ALIASES"),
        description="Comma-separated or JSON list of extra accepted JWT issuers.",
    )
    oidc_audience: str | None = Field(
        default=None,
        description="Optional JWT audience (client id). When unset, audience is not verified.",
    )
    oidc_jwks_url: str | None = Field(
        default=None,
        description="JWKS URL override. Defaults to {issuer}/protocol/openid-connect/certs",
    )
    oidc_jwks_json: str | None = Field(
        default=None,
        description="Inline JWKS JSON for tests (skips live JWKS fetch).",
    )

    keycloak_admin_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_ADMIN_URL", "KEYCLOAK_ADMIN_URL"),
        description="Keycloak base URL for Admin REST API (e.g. http://keycloak:8080).",
    )
    keycloak_admin_user: str = Field(
        default="admin",
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_ADMIN_USER", "KEYCLOAK_ADMIN_USER"),
    )
    keycloak_admin_password: str = Field(
        default="admin",
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_ADMIN_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD"),
    )
    keycloak_realm: str = Field(
        default="repody",
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_REALM", "KEYCLOAK_REALM"),
    )
    keycloak_admin_console_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUDIT_KEYCLOAK_ADMIN_CONSOLE_URL",
            "KEYCLOAK_ADMIN_CONSOLE_URL",
        ),
        description="Browser URL for the Keycloak admin console.",
    )
    keycloak_oauth_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUDIT_KEYCLOAK_CLIENT_ID", "AUTH_KEYCLOAK_ID"),
        description="OAuth client id for operator benchmark password-grant tokens.",
    )
    keycloak_oauth_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUDIT_KEYCLOAK_CLIENT_SECRET",
            "AUTH_KEYCLOAK_CLIENT_SECRET",
        ),
        description="OAuth client secret for operator benchmark password-grant tokens.",
    )
    operator_benchmark_bearer_token: str | None = Field(
        default=None,
        description="Pre-issued bearer token for benchmark_suite.py (skips Keycloak grant).",
    )
    operator_benchmark_user: str | None = Field(
        default=None,
        description="Keycloak user for operator benchmark jobs when OIDC is enabled.",
    )
    operator_benchmark_password: str | None = Field(
        default=None,
        description="Keycloak password for operator benchmark jobs when OIDC is enabled.",
    )

    def accepted_oidc_issuer_aliases(self) -> list[str]:
        return self._parse_oidc_issuer_aliases(self.oidc_issuer_aliases_env)

    @staticmethod
    def _parse_oidc_issuer_aliases(value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    inner = text.strip("[]")
                    return [part.strip() for part in inner.split(",") if part.strip()]
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            return [part.strip() for part in text.split(",") if part.strip()]
        return []
