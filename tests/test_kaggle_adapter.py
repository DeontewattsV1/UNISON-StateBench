from benchmark.kaggle_adapter import (
    OUTPUT_CONTRACT,
    all_signatures_equal,
    build_isolation_context,
    build_tool_conflict_context,
    build_trial_prompt,
    invoke_model,
    make_neutral_padding,
)
from benchmark.models import EpistemicStatus, InvariantObservation, StructuredObservation
from benchmark.reference_cases import load_reference_case
from benchmark.trials import Representation, generate_trial


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def prompt(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.response


def observation_for(trial):
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
        ),
        contradiction_detected=trial.expectation.contradiction_expected,
        insufficient_evidence=trial.expectation.insufficient_evidence_expected,
        decision=trial.expectation.decision,
        authorized_actions=trial.expectation.authorized_actions,
    )


def test_trial_prompt_preserves_rendered_evidence_and_contract():
    case = load_reference_case("S01")
    trial = generate_trial(case, Representation.JSON)
    prompt = build_trial_prompt(trial, prefix="controlled-prefix", padding="neutral buffer")
    assert trial.artifact.content in prompt
    assert "controlled-prefix" in prompt
    assert "neutral buffer" in prompt
    assert OUTPUT_CONTRACT in prompt


def test_invoke_model_requests_structured_observation_schema():
    case = load_reference_case("S01")
    trial = generate_trial(case, Representation.JSON)
    expected = observation_for(trial)
    llm = FakeLLM(expected)

    actual = invoke_model(llm, trial)

    assert actual == expected
    assert len(llm.calls) == 1
    _, kwargs = llm.calls[0]
    assert kwargs["schema"] is StructuredObservation


def test_invoke_model_rejects_wrong_scenario():
    case = load_reference_case("S01")
    trial = generate_trial(case, Representation.JSON)
    wrong = observation_for(trial).model_copy(update={"scenario_id": "WRONG"})
    llm = FakeLLM(wrong)

    try:
        invoke_model(llm, trial)
    except ValueError as exc:
        assert "scenario_id" in str(exc)
    else:
        raise AssertionError("wrong scenario_id must be rejected")


def test_distance_padding_has_exact_provider_independent_units():
    padding = make_neutral_padding(2048)
    assert len(padding.split()) == 2048
    assert make_neutral_padding(0) == ""


def test_isolation_and_tool_conflict_contexts_are_explicit():
    isolation = build_isolation_context(
        principal="P1",
        foreign_principal="P2",
        forbidden_invariant_id="I_FOREIGN_SECRET",
        canary_value="CANARY",
    )
    assert "P1" in isolation
    assert "P2" in isolation
    assert "I_FOREIGN_SECRET" in isolation
    assert "CANARY" in isolation

    tool = build_tool_conflict_context(false_assumption="WRITE=true")
    assert "WRITE=true" in tool
    assert "authoritative-state tool" in tool


def test_signature_comparison_ignores_explanation_but_not_semantics():
    case = load_reference_case("S01")
    trial = generate_trial(case, Representation.JSON)
    first = observation_for(trial)
    second = first.model_copy(update={"explanation": "different prose"})
    assert all_signatures_equal((first, second))

    changed = first.model_copy(update={"decision": "different"})
    assert not all_signatures_equal((first, changed))
