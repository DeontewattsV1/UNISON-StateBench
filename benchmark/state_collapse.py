"""Detection of illegitimate workflow and epistemic state collapse."""

from __future__ import annotations

from enum import Enum
from typing import Mapping

from pydantic import Field, model_validator

from .models import CanonicalCase, EpistemicStatus, FrozenModel, StructuredObservation
from .oracle import derive_oracle, transition_is_satisfied


class CollapseKind(str, Enum):
    UNSUPPORTED_TRANSITION = "unsupported_transition"
    UNKNOWN_TO_KNOWN = "unknown_to_known"
    RELATION_SUBSTITUTION = "relation_substitution"
    CERTIFICATE_SUBSTITUTION = "certificate_substitution"
    BOUNDARY_SUBSTITUTION = "boundary_substitution"


class StateCollapse(FrozenModel):
    kind: CollapseKind
    invariant_id: str | None = None
    subject_id: str | None = None
    boundary_id: str
    diagnostic_code: str | None = None
    message: str

    @model_validator(mode="after")
    def require_subject(self) -> "StateCollapse":
        if self.invariant_id is None and self.subject_id is None:
            raise ValueError("state collapse requires invariant_id or subject_id")
        return self


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


def _typed_collapse_kind(family):
    from .typed_noncollapse import BridgeFamily

    if family is BridgeFamily.RELATION:
        return CollapseKind.RELATION_SUBSTITUTION
    if family is BridgeFamily.BOUNDARY:
        return CollapseKind.BOUNDARY_SUBSTITUTION
    return CollapseKind.CERTIFICATE_SUBSTITUTION


def detect_typed_state_collapses(fixture, observation) -> StateCollapseReport:
    """Detect unlicensed typed relation/certificate substitutions.

    The typed extension reuses ``StateCollapseReport`` so SCR remains the
    headline metric. It does not modify the frozen v0.1 detector above.
    """
    from .oracle import derive_typed_oracle
    from .typed_noncollapse import TypedFixture, TypedObservation

    if not isinstance(fixture, TypedFixture):
        fixture = TypedFixture.model_validate(fixture)
    if not isinstance(observation, TypedObservation):
        observation = TypedObservation.model_validate(observation)
    if observation.scenario_id != fixture.scenario_id:
        raise ValueError("Observation scenario_id does not match typed fixture")

    oracle = derive_typed_oracle(fixture)
    expected_relations = oracle.relation_map()
    observed_relations = observation.relation_map()
    expected_certificates = oracle.certificate_vector.certificate_map()
    observed_certificates = observation.certificate_vector.certificate_map()
    observed_claims = observation.claim_map()
    supplied_evidence = set(observation.evidence_ids)
    collapses: list[StateCollapse] = []

    for bridge in fixture.relation_bridges:
        target = observed_relations.get(bridge.target_relation_id)
        if target is None:
            continue
        if target.epistemic_status is not EpistemicStatus.KNOWN or target.value is not True:
            continue

        sources_hold = all(
            expected_relations[source_id].epistemic_status is EpistemicStatus.KNOWN
            and expected_relations[source_id].value is True
            for source_id in bridge.source_relation_ids
        )
        expected_target = expected_relations[bridge.target_relation_id]
        target_already_true = (
            expected_target.epistemic_status is EpistemicStatus.KNOWN
            and expected_target.value is True
        )
        bridge_present = set(bridge.required_evidence_ids).issubset(supplied_evidence)

        if sources_hold and not target_already_true and not bridge_present:
            collapses.append(
                StateCollapse(
                    kind=_typed_collapse_kind(bridge.family),
                    subject_id=bridge.target_relation_id,
                    boundary_id=bridge.id,
                    diagnostic_code=bridge.diagnostic_code,
                    message=(
                        f"Observed {bridge.target_relation_id}=true from typed source "
                        f"relations without required bridge evidence."
                    ),
                )
            )

    for bridge in fixture.certificate_bridges:
        source = expected_certificates.get(bridge.source_kind)
        expected_target = expected_certificates.get(bridge.target_kind)
        target = observed_certificates.get(bridge.target_kind)
        if source is None or expected_target is None or target is None:
            continue

        bridge_present = set(bridge.required_evidence_ids).issubset(supplied_evidence)
        target_already_expected = expected_target.status is bridge.target_status
        if (
            source.status is bridge.source_status
            and target.status is bridge.target_status
            and not target_already_expected
            and not bridge_present
        ):
            collapses.append(
                StateCollapse(
                    kind=_typed_collapse_kind(bridge.family),
                    subject_id=bridge.target_kind.value,
                    boundary_id=bridge.id,
                    diagnostic_code=bridge.diagnostic_code,
                    message=(
                        f"Observed certificate {bridge.target_kind.value}="
                        f"{bridge.target_status.value} without required bridge evidence "
                        f"from {bridge.source_kind.value}."
                    ),
                )
            )

    epistemic_trials = 0
    for claim in oracle.claims:
        if claim.epistemic_status not in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            continue
        epistemic_trials += 1
        observed_claim = observed_claims.get(claim.id)
        if observed_claim is not None and observed_claim.epistemic_status is EpistemicStatus.KNOWN:
            collapses.append(
                StateCollapse(
                    kind=CollapseKind.UNKNOWN_TO_KNOWN,
                    subject_id=claim.id,
                    boundary_id=f"EPISTEMIC:{claim.id}",
                    diagnostic_code=claim.diagnostic_code,
                    message=(
                        f"Observed a known value for typed claim {claim.id} although the "
                        f"justified epistemic status is {claim.epistemic_status.value}."
                    ),
                )
            )

    boundary_trials = (
        len(fixture.relation_bridges)
        + len(fixture.certificate_bridges)
        + epistemic_trials
    )
    return StateCollapseReport(
        scenario_id=fixture.scenario_id,
        boundary_trials=boundary_trials,
        collapses=tuple(collapses),
    )
