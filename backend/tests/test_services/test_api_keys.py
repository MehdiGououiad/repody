from audit_workbench.services.api_keys import api_key_hint, hash_api_key, verify_api_key


def test_hash_and_verify_roundtrip() -> None:
    raw = "wbk_live_test_key_12345"
    digest = hash_api_key(raw)
    assert len(digest) == 64
    assert verify_api_key(raw, digest)
    assert not verify_api_key("wrong", digest)


def test_api_key_hint_masks_value() -> None:
    hint = api_key_hint("wbk_live_abcdef123456")
    assert hint.startswith("wbk_live_abc")
    assert "********" in hint
