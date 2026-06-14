from audit_workbench.services.run_lock import advisory_lock_key


def test_advisory_lock_key_is_stable() -> None:
    run_id = "AUD-TEST-1779292565646-21ef9956"
    assert advisory_lock_key(run_id) == advisory_lock_key(run_id)


def test_advisory_lock_key_differs_for_different_runs() -> None:
    a = advisory_lock_key("AUD-TEST-aaa")
    b = advisory_lock_key("AUD-TEST-bbb")
    assert a != b


def test_advisory_lock_key_is_positive_int64() -> None:
    key = advisory_lock_key("run-1")
    assert 0 <= key <= 0x7FFFFFFFFFFFFFFF
