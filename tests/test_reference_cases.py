from pathlib import Path

from benchmark.loaders import load_case
from benchmark.oracle import derive_oracle
from benchmark.reference_cases import load_reference_case, reference_case_names

ROOT = Path(__file__).resolve().parents[1]


def test_packaged_reference_cases_match_public_json():
    pairs = {
        "S01": ROOT / "cases" / "S01_capability_authorization.json",
        "S06": ROOT / "cases" / "S06_black_start_resilience.json",
        "S01_WRITE_GRANTED": ROOT / "cases" / "S01_write_granted_counterfactual.json",
    }
    assert set(reference_case_names()) == set(pairs)
    for name, path in pairs.items():
        assert load_reference_case(name) == load_case(path)


def test_u10_counterfactual_has_independent_oracle():
    baseline = load_reference_case("S01")
    changed = load_reference_case("S01_WRITE_GRANTED")

    baseline_oracle = derive_oracle(baseline)
    changed_oracle = derive_oracle(changed)

    assert baseline.scenario_id != changed.scenario_id
    assert baseline_oracle.decision == "deny_write"
    assert changed_oracle.decision == "allow_write"
    assert baseline_oracle.invariant_map()["I_WRITE_AUTHORIZED"].value is False
    assert changed_oracle.invariant_map()["I_WRITE_AUTHORIZED"].value is True
    assert baseline_oracle.transition_map()["T_AUTH_TO_WRITE"] is False
    assert changed_oracle.transition_map()["T_AUTH_TO_WRITE"] is True
