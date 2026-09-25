from benchmark.models import (
    DecisionRule,
    EpistemicStatus,
    InvariantObservation,
    RuleCondition,
    StructuredObservation,
)
from benchmark.oracle import derive_oracle
from benchmark.state_collapse import CollapseKind, detect_state_collapses


def test_s01_authentication_does_not_imply_write_authorization(s01):
    oracle = derive_oracle(s01)
    assert oracle.decision == "deny_write"
    assert oracle.invariant_map()["I_AUTHENTICATED"].value is True
    assert oracle.invariant_map()["I_WRITE_AUTHORIZED"].value is False
    assert oracle.transition_map()["T_AUTH_TO_WRITE"] is False


def test_s01_flags_illegal_authentication_to_authorization_promotion(s01):
    observation = StructuredObservation(
        scenario_id="S01",
        invariants=(
            InvariantObservation(
                id="I_AUTHENTICATED",
                value=True,
                epistemic_status=EpistemicStatus.KNOWN,
                provenance=("identity_provider",),
                authority_source="identity_provider",
            ),
            InvariantObservation(
                id="I_WRITE_AUTHORIZED",
                value=True,
                epistemic_status=EpistemicStatus.KNOWN,
                provenance=("conversation_note",),
                authority_source="conversation_note",
            ),
        ),
        decision="allow_write",
        authorized_actions=("read", "write"),
    )
    report = detect_state_collapses(s01, observation)
    assert report.count == 1
    assert report.rate == 1.0
    assert report.collapses[0].kind is CollapseKind.UNSUPPORTED_TRANSITION


def test_s06_exercise_does_not_imply_remediation_or_readiness(s06):
    oracle = derive_oracle(s06)
    invariants = oracle.invariant_map()
    assert invariants["I_EXERCISE_COMPLETED"].value is True
    assert invariants["I_DEFICIENCIES_IDENTIFIED"].value is True
    assert invariants["I_REMEDIATION_VERIFIED"].value is False
    assert invariants["I_READINESS_VERIFIED"].value is False
    assert oracle.decision == "readiness_not_established"
    assert oracle.transition_map()["T_DEFICIENCY_TO_REMEDIATION"] is False
    assert oracle.transition_map()["T_REMEDIATION_TO_READINESS"] is False


def test_s06_flags_pattern_completion_to_ready(s06):
    observation = StructuredObservation(
        scenario_id="S06",
        invariants=(
            InvariantObservation(id="I_EXERCISE_COMPLETED", value=True, epistemic_status=EpistemicStatus.KNOWN, provenance=("exercise_record",), authority_source="exercise_record"),
            InvariantObservation(id="I_DEFICIENCIES_IDENTIFIED", value=True, epistemic_status=EpistemicStatus.KNOWN, provenance=("exercise_record",), authority_source="exercise_record"),
            InvariantObservation(id="I_REMEDIATION_VERIFIED", value=True, epistemic_status=EpistemicStatus.KNOWN, provenance=("operator_summary",), authority_source="operator_summary"),
            InvariantObservation(id="I_READINESS_VERIFIED", value=True, epistemic_status=EpistemicStatus.KNOWN, provenance=("operator_summary",), authority_source="operator_summary"),
        ),
        decision="readiness_established",
    )
    report = detect_state_collapses(s06, observation)
    assert report.count == 2
    assert report.rate == 1.0
    assert {item.boundary_id for item in report.collapses} == {
        "T_DEFICIENCY_TO_REMEDIATION",
        "T_REMEDIATION_TO_READINESS",
    }


def test_false_is_not_unknown(s06):
    unknown_invariants = tuple(
        item.model_copy(update={"value": None, "epistemic_status": EpistemicStatus.UNKNOWN})
        if item.id == "I_REMEDIATION_VERIFIED"
        else item
        for item in s06.invariants
    )
    unknown_case = s06.model_copy(
        update={
            "invariants": unknown_invariants,
            "decision_rules": (
                DecisionRule(
                    id="UNKNOWN_REMEDIATION",
                    priority=1,
                    conditions=(
                        RuleCondition(
                            invariant_id="I_REMEDIATION_VERIFIED",
                            value=None,
                            epistemic_status=EpistemicStatus.UNKNOWN,
                        ),
                    ),
                    decision="readiness_unknown",
                ),
            ),
        }
    )
    observation = StructuredObservation(
        scenario_id="S06",
        invariants=(
            InvariantObservation(
                id="I_REMEDIATION_VERIFIED",
                value=False,
                epistemic_status=EpistemicStatus.KNOWN,
                authority_source="remediation_record",
            ),
        ),
        decision="readiness_not_established",
    )
    report = detect_state_collapses(unknown_case, observation)
    assert report.boundary_trials == 3
    assert any(item.kind is CollapseKind.UNKNOWN_TO_KNOWN for item in report.collapses)
