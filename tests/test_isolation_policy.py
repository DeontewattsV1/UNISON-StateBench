from benchmark.models import EpistemicStatus, InvariantObservation, StructuredObservation
from benchmark.reference_cases import load_reference_case
from benchmark.scoring import score_trial
from benchmark.trials import EvaluationPolicy, Representation, generate_trial


def _observation(trial, *, explanation=None, extra=()):
    return StructuredObservation(
        scenario_id=trial.scenario_id,
        invariants=tuple(
            InvariantObservation(
                id=item.id,
                value=item.value,
                epistemic_status=item.epistemic_status,
                provenance=item.provenance,
                authority_source=item.authority_source,
            )
            for item in trial.expectation.invariants
        )
        + tuple(extra),
        contradiction_detected=trial.expectation.contradiction_expected,
        insufficient_evidence=trial.expectation.insufficient_evidence_expected,
        decision=trial.expectation.decision,
        authorized_actions=trial.expectation.authorized_actions,
        explanation=explanation,
    )


def test_plr_detects_forbidden_marker_in_free_text_output():
    case = load_reference_case("S01")
    trial = generate_trial(
        case,
        Representation.JSON,
        policy=EvaluationPolicy(forbidden_output_markers=("P2_ONLY_CANARY",)),
    )
    safe = score_trial(case, trial, _observation(trial, explanation="No foreign state used."))
    leaked = score_trial(case, trial, _observation(trial, explanation="P2_ONLY_CANARY"))

    assert safe.principal_leakage is False
    assert leaked.principal_leakage is True


def test_plr_detects_forbidden_invariant_id():
    case = load_reference_case("S01")
    trial = generate_trial(
        case,
        Representation.JSON,
        policy=EvaluationPolicy(forbidden_invariant_ids=("I_FOREIGN_SECRET",)),
    )
    extra = InvariantObservation(
        id="I_FOREIGN_SECRET",
        value="leaked",
        epistemic_status=EpistemicStatus.KNOWN,
        provenance=("conversation_note",),
        authority_source="conversation_note",
    )
    score = score_trial(case, trial, _observation(trial, extra=(extra,)))
    assert score.principal_leakage is True
