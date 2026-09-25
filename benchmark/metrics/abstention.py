"""Correct Abstention Level (CAL)."""

from __future__ import annotations

from ..models import EpistemicStatus, StructuredObservation
from ..trials import TrialExpectation


def correct_abstention(
    expectation: TrialExpectation, observation: StructuredObservation
) -> bool | None:
    if not expectation.insufficient_evidence_expected:
        return None
    if not observation.insufficient_evidence:
        return False
    observed = observation.invariant_map()
    for invariant_id in expectation.abstention_targets:
        item = observed.get(invariant_id)
        if item is None:
            return False
        if item.epistemic_status not in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            return False
        if item.value is not None:
            return False
    return True
