from benchmark.oracle import derive_oracle


def test_s01_oracle_is_deterministic(s01):
    first = derive_oracle(s01)
    second = derive_oracle(s01)
    assert first == second
    assert first.decision == "deny_write"
    assert first.authorized_actions == ("read",)


def test_s06_oracle_is_deterministic(s06):
    first = derive_oracle(s06)
    second = derive_oracle(s06)
    assert first == second
    assert first.decision == "readiness_not_established"
