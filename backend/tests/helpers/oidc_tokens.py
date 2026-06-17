"""Mint RS256 JWTs for OIDC-enabled API tests."""

from __future__ import annotations

import json
import time
from functools import lru_cache

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_ISSUER = "http://test-issuer/realms/repody"


@lru_cache
def _rsa_keypair() -> tuple[rsa.RSAPrivateKey, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_pem.decode("utf-8")


def jwks_json_for_tests() -> str:
    private_key, public_pem = _rsa_keypair()
    public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    public_numbers = public_key.public_numbers()
    import base64

    def _b64_uint(val: int) -> str:
        length = (val.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(val.to_bytes(length, "big")).decode("ascii").rstrip("=")

    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "use": "sig",
        "alg": "RS256",
        "n": _b64_uint(public_numbers.n),
        "e": _b64_uint(public_numbers.e),
    }
    return json.dumps({"keys": [jwk]})


def mint_access_token(
    *,
    subject: str = "test-user",
    roles: list[str] | None = None,
    email: str = "test@repody.local",
    audience: str | list[str] | None = None,
) -> str:
    private_key, _ = _rsa_keypair()
    now = int(time.time())
    payload = {
        "sub": subject,
        "email": email,
        "iss": TEST_ISSUER,
        "iat": now,
        "exp": now + 3600,
        "realm_access": {"roles": roles or ["operator"]},
    }
    if audience is not None:
        payload["aud"] = audience
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
