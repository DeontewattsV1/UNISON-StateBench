import pytest

from benchmark.integrity import assert_unchanged, snapshot
from benchmark.transform_guard import run_guarded_transform


def test_canonical_and_oracle_hash_are_stable_across_read_only_projection(s06):
    before = snapshot(s06)
    evidence_view = {
        "scenario_id": s06.scenario_id,
        "states": [
            {"id": item.id, "value": item.value, "epistemic_status": item.epistemic_status.value}
            for item in s06.invariants
        ],
    }
    evidence_view["states"].reverse()
    evidence_view["states"].append({"synthetic_renderer_note": "presentation-only"})
    assert_unchanged(before, s06)


def test_canonical_models_are_deeply_frozen(s01):
    with pytest.raises(Exception):
        s01.invariants[0].value = False
    with pytest.raises(Exception):
        s01.canonical_state[0].value = "mutated"
    detached = s01.canonical_state_map()
    detached["principal"] = "P999"
    assert s01.canonical_state_map()["principal"] == "P1"


def test_guarded_transform_preserves_case_and_oracle(s06):
    def renderer(case):
        view = case.canonical_state_map()
        view["presentation_only"] = True
        return view

    result = run_guarded_transform(s06, renderer)
    assert result["presentation_only"] is True
    assert s06.canonical_state_map().get("presentation_only") is None


def test_guard_detects_even_forced_internal_mutation(s01):
    local = s01.model_copy(deep=True)

    def malicious_transform(case):
        # Deliberately bypass Pydantic's frozen assignment guard to prove that the
        # digest boundary catches canonical corruption even from bad transform code.
        object.__setattr__(case.invariants[0], "value", False)
        return "should-not-escape"

    with pytest.raises(AssertionError, match="Canonical state or deterministic oracle changed"):
        run_guarded_transform(local, malicious_transform)
