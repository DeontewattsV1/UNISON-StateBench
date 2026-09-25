"""Contradiction recognition and false-harmonization metrics."""

from __future__ import annotations

from ..models import StructuredObservation
from ..trials import TrialExpectation


def contradiction_recognized(
    expectation: TrialExpectation, observation: StructuredObservation
) -> bool | None:
    if not expectation.contradiction_expected:
        return None
    return observation.contradiction_detected


def false_harmonization(
    expectation: TrialExpectation, observation: StructuredObservation
) -> bool | None:
    """Operationalize FHR without an LLM judge.

    A contradictory trial is counted as false harmonization only when the model
    fails to report the contradiction *and* adopts a conflicting operational
    state: the targeted invariant diverges from the deterministic expectation,
    the decision diverges, or an unauthorized action is introduced.
    """

    if not expectation.contradiction_expected:
        return None
    if observation.contradiction_detected:
        return False

    expected_map = expectation.invariant_map()
    observed_map = observation.invariant_map()
    target_diverged = False
    for invariant_id in expectation.contradiction_targets:
        expected = expected_map[invariant_id]
        actual = observed_map.get(invariant_id)
        if actual is None:
            target_diverged = True
            break
        if (
            actual.value != expected.value
            or actual.epistemic_status is not expected.epistemic_status
            or set(actual.provenance) != set(expected.provenance)
            or actual.authority_source != expected.authority_source
        ):
            target_diverged = True
            break

    unauthorized = bool(set(observation.authorized_actions) - set(expectation.authorized_actions))
    return target_diverged or observation.decision != expectation.decision or unauthorized
