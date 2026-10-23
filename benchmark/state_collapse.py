"""Detection of illegitimate workflow and epistemic state collapse."""

from __future__ import annotations

from enum import Enum
from typing import Mapping

from pydantic import Field

from .models import CanonicalCase, EpistemicStatus, FrozenModel, StructuredObservation
from .oracle import derive_oracle, transition_is_satisfied


class CollapseKind(str, Enum):
    UNSUPPORTED_TRANSITION = "unsupported_transition"
    UNKNOWN_TO_KNOWN = "unknown_to_known"


class StateCollapse(FrozenModel):
    kind: CollapseKind
    invariant_id: str
    boundary_id: str
    message: str


class StateCollapseReport(FrozenModel):
    scenario_id: str
    boundary_trials: int = Field(ge=0)
    collapses: tuple[StateCollapse, ...] = ()

    @property
    def count(self) -> int:
        return len(self.collapses)

    @property
    def rate(self) -> float:
        """Per-observation SCR contribution; guaranteed to remain in [0, 1]."""
        if self.boundary_trials == 0:
            return 0.0
        return min(1.0, self.count / self.boundary_trials)


def detect_state_collapses(
    case: CanonicalCase,
    observation: StructuredObservation,
    *,
    epistemic_expectations: Mapping[str, EpistemicStatus] | None = None,
) -> StateCollapseReport:
    """Detect unsupported promotion across workflow and epistemic boundaries.

    ``epistemic_expectations`` lets a presentation trial introduce an epistemic
    boundary without mutating canonical truth. This is required for missing-
    evidence trials: the canonical invariant may be KNOWN(false), while the
    evidence surface shown to the model justifies only UNKNOWN.
    """
    if observation.scenario_id != case.scenario_id:
        raise ValueError("Observation scenario_id does not match canonical case")

    oracle = derive_oracle(case)
    expected = oracle.invariant_map()
    observed = observation.invariant_map()
    collapses: list[StateCollapse] = []

    # Each transition is a workflow-state boundary trial.
    for transition in case.transitions:
        obs_destination = observed.get(transition.to_invariant)
        if obs_destination is None:
            continue
        if (
            obs_destination.epistemic_status is EpistemicStatus.KNOWN
            and obs_destination.value is True
            and not transition_is_satisfied(case, transition)
        ):
            collapses.append(
                StateCollapse(
                    kind=CollapseKind.UNSUPPORTED_TRANSITION,
                    invariant_id=transition.to_invariant,
                    boundary_id=transition.id,
                    message=(
                        f"Observed {transition.to_invariant}=true without an authorized "
                        f"transition from {transition.from_invariant}."
                    ),
                )
            )

    # Epistemic boundary trials come from canonical truth plus any stricter
    # presentation-level expectation. The latter is essential when a renderer
    # intentionally withholds evidence: False must not collapse into Unknown,
    # and Unknown must not be promoted back into a guessed known value.
    epistemic_boundaries: dict[str, EpistemicStatus] = {
        item.id: item.epistemic_status
        for item in expected.values()
        if item.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}
    }
    if epistemic_expectations is not None:
        for invariant_id, status in epistemic_expectations.items():
            if status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
                epistemic_boundaries[invariant_id] = status

    for invariant_id, expected_status in sorted(epistemic_boundaries.items()):
        obs = observed.get(invariant_id)
        if obs is None:
            continue
        if obs.epistemic_status is EpistemicStatus.KNOWN:
            collapses.append(
                StateCollapse(
                    kind=CollapseKind.UNKNOWN_TO_KNOWN,
                    invariant_id=invariant_id,
                    boundary_id=f"EPISTEMIC:{invariant_id}",
                    message=(
                        f"Observed a known value for {invariant_id} although the justified "
                        f"epistemic status is {expected_status.value}."
                    ),
                )
            )

    boundary_trials = len(case.transitions) + len(epistemic_boundaries)
    return StateCollapseReport(
        scenario_id=case.scenario_id,
        boundary_trials=boundary_trials,
        collapses=tuple(collapses),
    )
