"""Hatchet task constants and client factory for ``repody_fraud``."""

from functools import cache

from hatchet_sdk import Hatchet

FRAUD_PRE_CHECK_TASK = "fraud.pre_check"
FRAUD_POST_VERIFY_TASK = "fraud.post_verify"


@cache
def hatchet() -> Hatchet:
    """Return cached Hatchet client (reads ``HATCHET_CLIENT_*`` on first use)."""
    return Hatchet()
