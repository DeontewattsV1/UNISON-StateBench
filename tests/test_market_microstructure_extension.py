import json
from pathlib import Path

from benchmark.loaders import load_case
from benchmark.oracle import derive_oracle, transition_is_satisfied
from empirical.plan import build_v01_plan

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extensions" / "market_microstructure"
CASE_DIR = EXTENSION / "cases"


def _extension_cases():
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    return tuple(load_case(CASE_DIR / name) for name in manifest["cases"])


def test_extension_is_explicitly_excluded_from_frozen_v01():
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / "cases" / "v0.1-corpus.json").read_text(encoding="utf-8"))
    assert manifest["included_in_unison_v0_1"] is False
    frozen_names = set(frozen["baseline_cases"]) | set(frozen["counterfactual_cases"])
    assert frozen_names.isdisjoint(manifest["cases"])


def test_extension_does_not_change_frozen_v01_plan_digest():
    plan = build_v01_plan(ROOT)
    frozen = json.loads(
        (ROOT / "experiments" / "v0.1" / "trial-matrix-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert plan.plan_digest == frozen["plan_digest"]
    assert plan.model_calls == 162


def test_all_market_extension_cases_load_and_derive_deterministic_oracles():
    cases = _extension_cases()
    assert tuple(case.scenario_id for case in cases) == ("M01", "M02", "M03", "M04", "M05")
    for case in cases:
        first = derive_oracle(case)
        second = derive_oracle(case)
        assert first == second


def test_no_unverified_market_transition_is_marked_observed():
    for case in _extension_cases():
        for transition in case.transitions:
            if not transition.observed:
                assert transition_is_satisfied(case, transition) is False


def test_signal_does_not_collapse_to_alpha():
    case = load_case(CASE_DIR / "M01_signal_vs_alpha.json")
    invariant = case.invariant_map()["I_ALPHA_VALIDATED"]
    assert invariant.value is None
    assert invariant.epistemic_status.value == "unknown"


def test_curve_intersection_does_not_establish_nash():
    case = load_case(CASE_DIR / "M02_equilibrium_condition.json")
    invariant = case.invariant_map()["I_NASH_EQUILIBRIUM_ESTABLISHED"]
    assert invariant.value is None
    assert invariant.epistemic_status.value == "unknown"


def test_kyle_result_remains_model_conditional():
    case = load_case(CASE_DIR / "M03_kyle_price_impact.json")
    assert case.invariant_map()["I_LAMBDA_FORMULA_MODEL_DERIVED"].value is True
    transfer = case.invariant_map()["I_UNIVERSAL_TRANSFER_VALIDATED"]
    assert transfer.value is None
    assert transfer.epistemic_status.value == "unknown"


def test_spread_optimality_is_not_claimed():
    case = load_case(CASE_DIR / "M04_spread_optimality.json")
    optimum = case.invariant_map()["I_OPTIMALITY_PROVEN"]
    assert optimum.value is None
    assert optimum.epistemic_status.value == "unknown"


def test_integrated_case_does_not_claim_trading_edge():
    case = load_case(CASE_DIR / "M05_integrated_auction_state.json")
    edge = case.invariant_map()["I_NET_EDGE_VALIDATED"]
    oracle = derive_oracle(case)
    assert edge.value is None
    assert edge.epistemic_status.value == "unknown"
    assert oracle.decision == "strategy_not_established"
