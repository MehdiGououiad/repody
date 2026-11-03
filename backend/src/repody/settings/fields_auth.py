from __future__ import annotations

import json

from pydantic import Field


class AuthSettingsFields:
    oidc_enabled: bool = Field(
        default=False,
        description="Require Keycloak JWT on management endpoints (disable for local pytest).",
    )
    oidc_issuer: str | None = Field(
        default=None,
        description="OIDC issuer URL, e.g. http://keycloak:8080/realms/repody",
    )
    oidc_issuer_aliases: str = Field(
        default="",
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

    def accepted_oidc_issuer_aliases(self) -> list[str]:
        return self._parse_oidc_issuer_aliases(self.oidc_issuer_aliases)

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
