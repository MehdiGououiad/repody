"""Environment-backed offline Ed25519 entitlement provider."""

from repody_common.entitlements import EntitlementState, verify_license_token
from repody_core.settings import get_settings


class EnvEntitlementProvider:
    """Verify the mounted offline Ed25519 license JWT without network calls."""

    def current(self) -> EntitlementState:
        settings = get_settings()
        token = settings.license_token.get_secret_value() if settings.license_token else None
        return verify_license_token(token, settings.license_public_key_pem)
