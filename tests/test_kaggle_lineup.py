from pathlib import Path

import pytest

from empirical.lineup import (
    assert_lineup_matches_plan,
    freeze_lineup,
    snapshot_runtime,
    validate_lineup_against_runtime,
)
from empirical.plan import build_v01_plan

ROOT = Path(__file__).resolve().parents[1]


class FakeKbench:
    def __init__(self, keys):
        self.llms = {key: object() for key in keys}


def test_runtime_snapshot_is_sorted_and_content_addressed():
    plan = build_v01_plan(ROOT)
    first = snapshot_runtime(
        FakeKbench(("vendor/zeta", "vendor/alpha")),
        plan,
        runtime_metadata={"surface": "test"},
    )
    second = snapshot_runtime(
        FakeKbench(("vendor/alpha", "vendor/zeta")),
        plan,
        runtime_metadata={"surface": "test"},
    )
    assert first.available_model_keys == ("vendor/alpha", "vendor/zeta")
    assert first.snapshot_digest == second.snapshot_digest


def test_frozen_lineup_preserves_operator_order_and_total_calls():
    plan = build_v01_plan(ROOT)
    snapshot = snapshot_runtime(
        FakeKbench(("vendor/a", "vendor/b", "vendor/c")),
        plan,
    )
    lineup = freeze_lineup(
        snapshot,
        ("vendor/c", "vendor/a"),
        calls_per_model=plan.model_calls,
    )
    assert lineup.selected_model_keys == ("vendor/c", "vendor/a")
    assert lineup.model_count == 2
    assert lineup.calls_per_model == 162
    assert lineup.total_model_calls == 324
    assert_lineup_matches_plan(lineup, plan)


def test_frozen_lineup_is_deterministic():
    plan = build_v01_plan(ROOT)
    snapshot = snapshot_runtime(FakeKbench(("vendor/a", "vendor/b")), plan)
    one = freeze_lineup(snapshot, ("vendor/a", "vendor/b"), calls_per_model=162)
    two = freeze_lineup(snapshot, ("vendor/a", "vendor/b"), calls_per_model=162)
    assert one == two
    assert one.lineup_digest == two.lineup_digest


def test_unavailable_key_cannot_be_frozen():
    plan = build_v01_plan(ROOT)
    snapshot = snapshot_runtime(FakeKbench(("vendor/a",)), plan)
    with pytest.raises(ValueError, match="not present"):
        freeze_lineup(snapshot, ("vendor/missing",), calls_per_model=162)


def test_duplicate_or_empty_lineup_is_rejected():
    plan = build_v01_plan(ROOT)
    snapshot = snapshot_runtime(FakeKbench(("vendor/a",)), plan)
    with pytest.raises(ValueError, match="At least one"):
        freeze_lineup(snapshot, (), calls_per_model=162)
    with pytest.raises(ValueError, match="duplicate"):
        freeze_lineup(snapshot, ("vendor/a", "vendor/a"), calls_per_model=162)


def test_runtime_drift_fails_closed_for_frozen_lineup():
    plan = build_v01_plan(ROOT)
    snapshot = snapshot_runtime(FakeKbench(("vendor/a", "vendor/b")), plan)
    lineup = freeze_lineup(snapshot, ("vendor/a", "vendor/b"), calls_per_model=162)

    with pytest.raises(ValueError, match="unavailable"):
        validate_lineup_against_runtime(FakeKbench(("vendor/a",)), lineup)


def test_empty_runtime_snapshot_is_rejected():
    plan = build_v01_plan(ROOT)
    with pytest.raises(ValueError, match="no model keys"):
        snapshot_runtime(FakeKbench(()), plan)
