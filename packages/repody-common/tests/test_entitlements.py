"""Unit tests for offline Ed25519 license verification."""

from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from repody_common.entitlements import (
    LicenseClaims,
    sign_license_token,
    verify_license_token,
)


def _ed25519_keypair() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def test_active_license_grants_only_entitled_modules() -> None:
    private_pem, public_pem = _ed25519_keypair()
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    token = sign_license_token(
        LicenseClaims(
            customer_id="bank-atlas",
            modules=("idp", "fraud"),
            issued_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=365),
        ),
        private_pem,
    )

    state = verify_license_token(token, public_pem, now=now)
    assert state.status == "active"
    assert state.is_operational is True
    assert state.customer_id == "bank-atlas"
    assert state.has_module("idp") is True
    assert state.has_module("fraud") is True
    assert state.has_module("operator") is False


def test_expired_license_enters_soft_grace_then_expires() -> None:
    private_pem, public_pem = _ed25519_keypair()
    issued = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    expires = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)
    token = sign_license_token(
        LicenseClaims(
            customer_id="bank-atlas",
            modules=("fraud",),
            issued_at=issued,
            expires_at=expires,
            grace_days=30,
        ),
        private_pem,
    )

    during_grace = verify_license_token(token, public_pem, now=expires + timedelta(days=10))
    assert during_grace.status == "grace"
    assert during_grace.is_operational is True
    assert during_grace.has_module("fraud") is True
    assert during_grace.warning is not None

    past_grace = verify_license_token(token, public_pem, now=expires + timedelta(days=31))
    assert past_grace.status == "expired"
    assert past_grace.is_operational is False
    assert past_grace.has_module("fraud") is False
    assert past_grace.modules == ()


def test_invalid_signature_wrong_key_and_unconfigured_are_rejected() -> None:
    private_pem, public_pem = _ed25519_keypair()
    _, other_public_pem = _ed25519_keypair()
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    token = sign_license_token(
        LicenseClaims(
            customer_id="bank-atlas",
            modules=("idp",),
            issued_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=30),
        ),
        private_pem,
    )

    assert verify_license_token(None, public_pem, now=now).status == "unconfigured"
    assert verify_license_token(token, None, now=now).status == "unconfigured"

    wrong_key = verify_license_token(token, other_public_pem, now=now)
    assert wrong_key.status == "invalid"
    assert wrong_key.has_module("idp") is False

    tampered = f"{token[:-4]}aaaa"
    assert verify_license_token(tampered, public_pem, now=now).status == "invalid"
