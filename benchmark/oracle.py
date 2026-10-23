"""Deterministic oracle derivation for UNISON-StateBench v0.1."""

from __future__ import annotations

from .models import (
    CanonicalCase,
    DecisionRule,
    EpistemicStatus,
    OracleInvariant,
    OracleResult,
    OracleTransitionState,
    RuleCondition,
    TransitionRequirement,
)


class OracleDerivationError(ValueError):
    """Raised when canonical truth and transition requirements are inconsistent."""


def transition_is_satisfied(case: CanonicalCase, transition: TransitionRequirement) -> bool:
    """Whether an observed transition is backed by present trusted evidence."""
    if not transition.observed:
        return False

    evidence_map = case.evidence_map()
    source_map = case.source_map()
    for evidence_id in transition.required_evidence:
        evidence = evidence_map[evidence_id]
        if not evidence.present or not evidence.supports_transition:
            return False
        source = source_map[evidence.source_id]
        if source.authority_rank < transition.minimum_authority_rank or not source.trusted:
            return False
    return True


def _condition_matches(case: CanonicalCase, condition: RuleCondition) -> bool:
    invariant = case.invariant_map()[condition.invariant_id]
    if condition.epistemic_status is not None and invariant.epistemic_status is not condition.epistemic_status:
        return False
    if condition.value is not None:
        return invariant.value == condition.value
    if condition.epistemic_status is None:
        return invariant.value is None
    return True


def _select_decision_rule(case: CanonicalCase) -> DecisionRule:
    for rule in sorted(case.decision_rules, key=lambda item: item.priority):
        if all(_condition_matches(case, condition) for condition in rule.conditions):
            return rule
    raise OracleDerivationError(
        f"No deterministic decision rule matched scenario {case.scenario_id}"
    )


def _derive_transition_states(case: CanonicalCase) -> tuple[OracleTransitionState, ...]:
    states: list[OracleTransitionState] = []
    invariant_map = case.invariant_map()
    for transition in case.transitions:
        satisfied = transition_is_satisfied(case, transition)
        destination = invariant_map[transition.to_invariant]
        if (
            destination.epistemic_status is EpistemicStatus.KNOWN
            and destination.value is True
            and not satisfied
        ):
            raise OracleDerivationError(
                f"Canonical case {case.scenario_id} illegally promotes "
                f"{transition.to_invariant}=true across unsatisfied transition "
                f"{transition.id}"
            )
        states.append(OracleTransitionState(id=transition.id, satisfied=satisfied))
    return tuple(states)


def derive_oracle(case: CanonicalCase) -> OracleResult:
    """Derive expected output only from frozen canonical state and declarative rules."""
    transition_states = _derive_transition_states(case)
    rule = _select_decision_rule(case)
    invariants = tuple(
        OracleInvariant(
            id=item.id,
            value=item.value,
            epistemic_status=item.epistemic_status,
            provenance=item.provenance,
            authority=item.authority,
        )
        for item in case.invariants
    )
    return OracleResult(
        scenario_id=case.scenario_id,
        invariants=invariants,
        decision=rule.decision,
        authorized_actions=rule.authorized_actions,
        transitions=transition_states,
    )
