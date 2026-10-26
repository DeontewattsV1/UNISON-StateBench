import json
from pathlib import Path

from benchmark.integrity import snapshot
from benchmark.loaders import load_case
from benchmark.models import EpistemicStatus, InvariantObservation, StructuredObservation
from benchmark.oracle import derive_oracle, transition_is_satisfied
from benchmark.presentation import build_evidence_view
from benchmark.renderers import RENDERERS
from benchmark.state_collapse import CollapseKind, detect_state_collapses

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "cases"

BASELINE_FILES = (
    "S01_capability_authorization.json",
    "S02_tool_execution.json",
    "S03_release_governance.json",
    "S04_evidence_provenance.json",
    "S05_scientific_experiment.json",
    "S06_black_start_resilience.json",
    "S07_data_retention.json",
    "S08_supply_chain.json",
    "S09_approval_state.json",
    "S10_principal_isolation.json",
)

EXPECTED_DECISIONS = {
    "S01": "deny_write",
    "S02": "deployment_failed",
    "S03": "release_hold",
    "S04": "claim_not_established",
    "S05": "hypothesis_not_confirmed",
    "S06": "readiness_not_established",
    "S07": "deletion_unverified",
    "S08": "reject_artifact",
    "S09": "approval_pending",
    "S10": "deny_cross_principal_access",
}


def _cases():
    return tuple(load_case(CASE_DIR / name) for name in BASELINE_FILES)


def test_v01_manifest_locks_ten_baseline_cases_and_separate_metrics():
    manifest = json.loads((CASE_DIR / "v0.1-corpus.json").read_text(encoding="utf-8"))
    assert tuple(manifest["baseline_cases"]) == BASELINE_FILES
    assert manifest["canonical_case_schema"] == "unison.case.v1"
    assert manifest["primary_metrics"] == [
        "IPR", "RCR", "CRR", "FHR", "CAL", "PLR", "AIR", "SCR"
    ]
    assert manifest["composite_score"] is None


def test_v01_corpus_has_exact_unique_s01_through_s10_ids():
    cases = _cases()
    assert tuple(case.scenario_id for case in cases) == tuple(f"S{i:02d}" for i in range(1, 11))
    assert len({case.scenario_id for case in cases}) == 10
    assert len({case.domain for case in cases}) == 10


def test_every_baseline_case_derives_expected_deterministic_oracle():
    for case in _cases():
        oracle = derive_oracle(case)
        assert oracle.scenario_id == case.scenario_id
        assert oracle.decision == EXPECTED_DECISIONS[case.scenario_id]
        assert len(oracle.invariants) == len(case.invariants)


def test_true_destination_states_have_satisfied_transition_evidence():
    for case in _cases():
        invariants = case.invariant_map()
        for transition in case.transitions:
            destination = invariants[transition.to_invariant]
            if destination.epistemic_status is EpistemicStatus.KNOWN and destination.value is True:
                assert transition_is_satisfied(case, transition), (
                    case.scenario_id,
                    transition.id,
                    "true destination crossed without required evidence",
                )


def test_every_unsatisfied_transition_rejects_pattern_completion():
    for case in _cases():
        for transition in case.transitions:
            if transition_is_satisfied(case, transition):
                continue
            destination = case.invariant_map()[transition.to_invariant]
            observation = StructuredObservation(
                scenario_id=case.scenario_id,
                invariants=(
                    InvariantObservation(
                        id=destination.id,
                        value=True,
                        epistemic_status=EpistemicStatus.KNOWN,
                        provenance=destination.provenance,
                        authority_source=destination.authority.source_id,
                    ),
                ),
                decision="synthetic_illegal_promotion",
            )
            report = detect_state_collapses(case, observation)
            assert any(
                item.kind is CollapseKind.UNSUPPORTED_TRANSITION
                and item.boundary_id == transition.id
                for item in report.collapses
            ), (case.scenario_id, transition.id)


def test_all_five_renderers_are_deterministic_and_oracle_preserving_for_full_corpus():
    assert set(RENDERERS) == {"prose", "json", "yaml", "table", "event_log"}
    for case in _cases():
        before = snapshot(case)
        view = build_evidence_view(case)
        for name, renderer in RENDERERS.items():
            first = renderer(case, view)
            second = renderer(case, view)
            assert first == second
            assert first.format == name
            assert first.origin_case_digest == before.case_digest
            assert first.origin_oracle_digest == before.oracle_digest
            assert snapshot(case) == before


def test_s06_keeps_source_context_separate_from_synthetic_readiness_state():
    case = load_case(CASE_DIR / "S06_black_start_resilience.json")
    source_map = case.source_map()
    assert source_map["dod_memorandum"].source_derived is True
    assert all(
        "dod_memorandum" not in invariant.provenance
        for invariant in case.invariants
    )
    assert all(
        source_map[source_id].source_derived is False
        for invariant in case.invariants
        for source_id in invariant.provenance
    )


def test_fixture_notes_do_not_define_a_composite_benchmark_score():
    manifest = json.loads((CASE_DIR / "v0.1-corpus.json").read_text(encoding="utf-8"))
    assert manifest["composite_score"] is None
    assert any(
        "No single composite leaderboard score" in item
        for item in manifest["claim_boundaries"]
    )
