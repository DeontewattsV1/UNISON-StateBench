import pytest

from benchmark.integrity import snapshot
from benchmark.trials import (
    EvaluationPolicy,
    MutationKind,
    MutationPlan,
    Representation,
    derive_trial_expectation,
    generate_trial,
    generate_trial_matrix,
)


def test_trial_generation_is_deterministic_and_preserves_oracle(s06):
    before = snapshot(s06)
    plan = MutationPlan(
        kind=MutationKind.AUTHORITY_CONFLICT,
        invariant_id="I_REMEDIATION_VERIFIED",
        source_id="operator_summary",
        replacement_value=True,
    )
    first = generate_trial(s06, Representation.JSON, plan)
    second = generate_trial(s06, Representation.JSON, plan)
    assert first == second
    assert first.expectation.contradiction_expected is True
    assert first.expectation.invariant_map()["I_REMEDIATION_VERIFIED"].value is False
    assert '"kind": "authority_conflict"' in first.artifact.content
    assert snapshot(s06) == before


def test_missing_evidence_changes_trial_epistemic_state_not_canonical_truth(s01):
    before = snapshot(s01)
    plan = MutationPlan(kind=MutationKind.MISSING, invariant_id="I_WRITE_AUTHORIZED")
    expectation = derive_trial_expectation(s01, plan, EvaluationPolicy(authorization_sensitive=True))
    missing = expectation.invariant_map()["I_WRITE_AUTHORIZED"]
    assert missing.value is None
    assert missing.epistemic_status.value == "unknown"
    assert missing.provenance == ()
    assert missing.authority_source == "capability_ledger"
    assert expectation.insufficient_evidence_expected is True
    assert expectation.decision == "insufficient_evidence"
    assert s01.invariant_map()["I_WRITE_AUTHORIZED"].value is False
    assert snapshot(s01) == before


def test_matrix_is_case_x_representation_x_mutation_cartesian_product(s06):
    reps = (Representation.PROSE, Representation.JSON, Representation.TABLE)
    plans = (MutationPlan(), MutationPlan(kind=MutationKind.PARAPHRASE))
    trials = generate_trial_matrix((s06,), reps, plans)
    assert len(trials) == 6
    assert len({item.trial_id for item in trials}) == 6
    assert len({item.equivalence_group for item in trials}) == 2


def test_targeted_plan_rejects_missing_invariant(s01):
    with pytest.raises(ValueError, match="does not exist"):
        generate_trial(
            s01,
            Representation.JSON,
            MutationPlan(kind=MutationKind.MISSING, invariant_id="I_NOT_REAL"),
        )


def test_truth_changing_intervention_is_not_a_mutation_plan():
    with pytest.raises(ValueError, match="does not accept parameters"):
        MutationPlan(kind=MutationKind.NONE, invariant_id="I_WRITE_AUTHORIZED")
