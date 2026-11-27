"""Offline Ed25519 license verification with soft grace period."""

from datetime import UTC, datetime, timedelta
from typing import Literal, Self

import jwt
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, model_validator

ModuleId = Literal["idp", "fraud", "operator"]
LicenseStatus = Literal["active", "grace", "expired", "invalid", "unconfigured"]

_MODULES_ADAPTER: TypeAdapter[tuple[ModuleId, ...]] = TypeAdapter(tuple[ModuleId, ...])


class LicenseClaims(BaseModel):
    """Claims embedded in an offline Ed25519-signed Repody license JWT."""

    customer_id: str = Field(min_length=1)
    modules: tuple[ModuleId, ...] = Field(min_length=1)
    seats: int | None = Field(default=None, ge=1)
    issued_at: datetime
    expires_at: datetime
    grace_days: int = Field(default=30, ge=0)
    support_tier: str = Field(default="enterprise", min_length=1)

    @model_validator(mode="after")
    def _validate_window(self) -> Self:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware.")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be strictly after issued_at.")
        return self


class EntitlementState(BaseModel):
    """Verified runtime entitlement state exposed by ``repody-core``."""

    status: LicenseStatus
    modules: tuple[ModuleId, ...] = ()
    customer_id: str | None = None
    expires_at: datetime | None = None
    grace_ends_at: datetime | None = None
    warning: str | None = None

    @property
    def is_operational(self) -> bool:
        """True while the license is active or inside its soft grace window."""
        return self.status in ("active", "grace")

    def has_module(self, module: ModuleId) -> bool:
        """Whether ``module`` is currently licensed and operational."""
        return self.is_operational and module in self.modules


def sign_license_token(claims: LicenseClaims, private_key_pem: str) -> str:
    """Sign an offline Ed25519 (``EdDSA``) license JWT."""
    payload = {
        "sub": claims.customer_id,
        "iat": int(claims.issued_at.timestamp()),
        "exp": int(claims.expires_at.timestamp()),
        "modules": list(claims.modules),
        "seats": claims.seats,
        "grace_days": claims.grace_days,
        "support_tier": claims.support_tier,
    }
    return jwt.encode(payload, private_key_pem, algorithm="EdDSA")


def verify_license_token(
    token: str | None,
    public_key_pem: str | None,
    *,
    now: datetime | None = None,
) -> EntitlementState:
    """Verify an offline Ed25519 license JWT without network calls.

    Enforces ``algorithms=["EdDSA"]`` to prevent algorithm confusion and models a
    configurable soft grace period past ``exp`` so production banking workloads do
    not halt abruptly on contract renewal dates.
    """
    clean_token = (token or "").strip()
    clean_key = (public_key_pem or "").strip()
    if not clean_token or not clean_key:
        return EntitlementState(
            status="unconfigured",
            warning="No offline license token or public key is configured.",
        )

    try:
        decoded = jwt.decode(
            clean_token,
            clean_key,
            algorithms=["EdDSA"],
            options={"verify_exp": False, "require": ["sub", "iat", "exp", "modules"]},
        )
        customer_id = str(decoded["sub"]).strip()
        if not customer_id:
            raise ValueError("License subject (sub) is empty.")
        modules = _MODULES_ADAPTER.validate_python(decoded["modules"])
        if not modules:
            raise ValueError("License grants no modules.")
        issued_at = datetime.fromtimestamp(float(decoded["iat"]), tz=UTC)
        expires_at = datetime.fromtimestamp(float(decoded["exp"]), tz=UTC)
        raw_grace = decoded.get("grace_days", 30)
        if not isinstance(raw_grace, int) or isinstance(raw_grace, bool) or raw_grace < 0:
            raise ValueError("grace_days must be a non-negative integer.")
        grace_days = raw_grace
    except (jwt.PyJWTError, ValidationError, ValueError, TypeError) as exc:
        return EntitlementState(status="invalid", warning=f"Invalid license: {exc}")

    current = (now or datetime.now(UTC)).astimezone(UTC)
    if current < issued_at:
        return EntitlementState(
            status="invalid",
            warning="License issued_at timestamp is in the future.",
        )

    grace_ends_at = expires_at + timedelta(days=grace_days)
    deduped_modules = tuple(dict.fromkeys(modules))

    if current <= expires_at:
        return EntitlementState(
            status="active",
            modules=deduped_modules,
            customer_id=customer_id,
            expires_at=expires_at,
            grace_ends_at=grace_ends_at,
        )

    if current <= grace_ends_at:
        return EntitlementState(
            status="grace",
            modules=deduped_modules,
            customer_id=customer_id,
            expires_at=expires_at,
            grace_ends_at=grace_ends_at,
            warning=(
                f"License expired on {expires_at.date().isoformat()}; operating in "
                f"{grace_days}-day soft grace period until {grace_ends_at.date().isoformat()}."
            ),
        )

    return EntitlementState(
        status="expired",
        modules=(),
        customer_id=customer_id,
        expires_at=expires_at,
        grace_ends_at=grace_ends_at,
        warning=f"License expired on {expires_at.date().isoformat()} and grace period ended.",
    )
