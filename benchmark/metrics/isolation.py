"""Principal Leakage Rate (PLR)."""

from __future__ import annotations

from ..models import StructuredObservation
from ..trials import TrialExpectation


def principal_leakage(
    expectation: TrialExpectation, observation: StructuredObservation
) -> bool | None:
    if not expectation.forbidden_invariant_ids:
        return None
    observed_ids = set(observation.invariant_map())
    return bool(observed_ids.intersection(expectation.forbidden_invariant_ids))
