"""Deterministic trial planning and generation for UNISON-StateBench v0.1.

This layer sits between immutable canonical truth and future Kaggle task wrappers.
It constructs presentation-only trials as a cartesian product of:

    CanonicalCase × Representation × MutationPlan

The canonical case and canonical oracle are never rewritten. A trial receives a
separate deterministic expectation describing what is justified by the evidence
surface shown to the model. This is what lets U05 preserve the constitutional
rule ``False != Unknown`` without mutating reference truth.
"""

from __future__ import annotations

from enum import Enum
from hashlib import sha256
from itertools import product
from typing import Iterable

from pydantic import model_validator

from .models import (
    CanonicalCase,
    EpistemicStatus,
    FrozenModel,
    JsonScalar,
    RuleCondition,
)
from .mutations import (
    adversarial_flip,
    inject_authority_conflict,
    inject_contradiction,
    paraphrase_view,
    remove_invariant_evidence,
    reorder_view,
)
from .oracle import derive_oracle
from .presentation import EvidenceView, RenderedArtifact, build_evidence_view
from .renderers import RENDERERS


class Representation(str, Enum):
    PROSE = "prose"
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    EVENT_LOG = "event_log"


class MutationKind(str, Enum):
    NONE = "none"
    REORDER = "reorder"
    PARAPHRASE = "paraphrase"
    CONTRADICTION = "contradiction"
    MISSING = "missing"
    AUTHORITY_CONFLICT = "authority_conflict"
    ADVERSARIAL = "adversarial"


class MutationPlan(FrozenModel):
    """One deterministic presentation-only mutation.

    U10 truth-changing interventions are intentionally *not* represented here.
    Such interventions must construct a separate CanonicalCase and derive a new
    canonical oracle before trial generation.
    """

    kind: MutationKind = MutationKind.NONE
    invariant_id: str | None = None
    source_id: str | None = None
    replacement_value: JsonScalar = None
    mode: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "MutationPlan":
        target_required = {
            MutationKind.CONTRADICTION,
            MutationKind.MISSING,
            MutationKind.AUTHORITY_CONFLICT,
            MutationKind.ADVERSARIAL,
        }
        if self.kind in target_required and not self.invariant_id:
            raise ValueError(f"Mutation {self.kind.value} requires invariant_id")
        if self.kind in {MutationKind.NONE, MutationKind.PARAPHRASE}:
            if any(
                item is not None
                for item in (self.invariant_id, self.source_id, self.mode)
            ) or self.replacement_value is not None:
                raise ValueError(f"Mutation {self.kind.value} does not accept parameters")
        if self.kind is MutationKind.REORDER and self.mode not in {None, "reverse", "rotate_left"}:
            raise ValueError("Reorder mode must be reverse or rotate_left")
        if self.kind not in {
            MutationKind.CONTRADICTION,
            MutationKind.AUTHORITY_CONFLICT,
            MutationKind.ADVERSARIAL,
        } and self.replacement_value is not None:
            raise ValueError(f"Mutation {self.kind.value} does not accept replacement_value")
        return self

    def stable_key(self) -> str:
        payload = self.model_dump_json(exclude_none=False)
        return sha256(payload.encode("utf-8")).hexdigest()[:16]


class EvaluationPolicy(FrozenModel):
    """Metric applicability that is orthogonal to the presentation mutation."""

    authorization_sensitive: bool = False
    forbidden_invariant_ids: tuple[str, ...] = ()
    forbidden_output_markers: tuple[str, ...] = ()


class ExpectedInvariant(FrozenModel):
    id: str
    value: JsonScalar
    epistemic_status: EpistemicStatus
    provenance: tuple[str, ...]
    authority_source: str
    required: bool = True


class TrialExpectation(FrozenModel):
    scenario_id: str
    invariants: tuple[ExpectedInvariant, ...]
    decision: str
    authorized_actions: tuple[str, ...] = ()
    contradiction_expected: bool = False
    insufficient_evidence_expected: bool = False
    contradiction_targets: tuple[str, ...] = ()
    abstention_targets: tuple[str, ...] = ()
    authorization_sensitive: bool = False
    forbidden_invariant_ids: tuple[str, ...] = ()
    forbidden_output_markers: tuple[str, ...] = ()

    def invariant_map(self) -> dict[str, ExpectedInvariant]:
        return {item.id: item for item in self.invariants}


class GeneratedTrial(FrozenModel):
    trial_id: str
    equivalence_group: str
    scenario_id: str
    representation: Representation
    mutation: MutationPlan
    expectation: TrialExpectation
    artifact: RenderedArtifact


def _expected_from_oracle(case: CanonicalCase) -> list[ExpectedInvariant]:
    oracle = derive_oracle(case)
    required_map = {item.id: item.required for item in case.invariants}
    return [
        ExpectedInvariant(
            id=item.id,
            value=item.value,
            epistemic_status=item.epistemic_status,
            provenance=item.provenance,
            authority_source=item.authority.source_id,
            required=required_map[item.id],
        )
        for item in oracle.invariants
    ]


def _condition_matches_expected(
    invariant_map: dict[str, ExpectedInvariant], condition: RuleCondition
) -> bool:
    invariant = invariant_map[condition.invariant_id]
    if condition.epistemic_status is not None and invariant.epistemic_status is not condition.epistemic_status:
        return False
    if condition.value is not None:
        return invariant.value == condition.value
    if condition.epistemic_status is None:
        return invariant.value is None
    return True


def _derive_visible_decision(
    case: CanonicalCase, expected: tuple[ExpectedInvariant, ...]
) -> tuple[str, tuple[str, ...]]:
    by_id = {item.id: item for item in expected}
    for rule in sorted(case.decision_rules, key=lambda item: item.priority):
        if all(_condition_matches_expected(by_id, condition) for condition in rule.conditions):
            return rule.decision, rule.authorized_actions
    return "insufficient_evidence", ()


def derive_trial_expectation(
    case: CanonicalCase,
    mutation: MutationPlan,
    policy: EvaluationPolicy | None = None,
) -> TrialExpectation:
    """Derive the deterministic expected observation for a presentation trial."""

    policy = policy or EvaluationPolicy()
    expected = _expected_from_oracle(case)
    contradiction_expected = mutation.kind in {
        MutationKind.CONTRADICTION,
        MutationKind.AUTHORITY_CONFLICT,
    }
    insufficient = mutation.kind is MutationKind.MISSING
    contradiction_targets: tuple[str, ...] = ()
    abstention_targets: tuple[str, ...] = ()

    if mutation.invariant_id is not None and mutation.invariant_id not in case.invariant_map():
        raise ValueError(
            f"Mutation target {mutation.invariant_id!r} does not exist in {case.scenario_id}"
        )

    if mutation.kind is MutationKind.MISSING:
        assert mutation.invariant_id is not None
        abstention_targets = (mutation.invariant_id,)
        expected = [
            item.model_copy(
                update={
                    "value": None,
                    "epistemic_status": EpistemicStatus.UNKNOWN,
                    "provenance": (),
                }
            )
            if item.id == mutation.invariant_id
            else item
            for item in expected
        ]

    if contradiction_expected:
        assert mutation.invariant_id is not None
        contradiction_targets = (mutation.invariant_id,)

    expected_tuple = tuple(expected)
    if mutation.kind is MutationKind.MISSING:
        decision, actions = _derive_visible_decision(case, expected_tuple)
    else:
        oracle = derive_oracle(case)
        decision, actions = oracle.decision, oracle.authorized_actions

    return TrialExpectation(
        scenario_id=case.scenario_id,
        invariants=expected_tuple,
        decision=decision,
        authorized_actions=actions,
        contradiction_expected=contradiction_expected,
        insufficient_evidence_expected=insufficient,
        contradiction_targets=contradiction_targets,
        abstention_targets=abstention_targets,
        authorization_sensitive=policy.authorization_sensitive,
        forbidden_invariant_ids=policy.forbidden_invariant_ids,
        forbidden_output_markers=policy.forbidden_output_markers,
    )


def apply_mutation(
    case: CanonicalCase,
    view: EvidenceView,
    plan: MutationPlan,
) -> EvidenceView:
    if plan.kind is MutationKind.NONE:
        return view
    if plan.kind is MutationKind.REORDER:
        return reorder_view(case, view, mode=plan.mode or "reverse")
    if plan.kind is MutationKind.PARAPHRASE:
        return paraphrase_view(case, view)
    if plan.kind is MutationKind.CONTRADICTION:
        assert plan.invariant_id is not None
        return inject_contradiction(
            case,
            view,
            invariant_id=plan.invariant_id,
            source_id=plan.source_id,
            conflicting_value=plan.replacement_value,
        )
    if plan.kind is MutationKind.MISSING:
        assert plan.invariant_id is not None
        return remove_invariant_evidence(case, view, invariant_id=plan.invariant_id)
    if plan.kind is MutationKind.AUTHORITY_CONFLICT:
        assert plan.invariant_id is not None
        return inject_authority_conflict(
            case,
            view,
            invariant_id=plan.invariant_id,
            lower_source_id=plan.source_id,
            conflicting_value=plan.replacement_value,
        )
    if plan.kind is MutationKind.ADVERSARIAL:
        assert plan.invariant_id is not None
        return adversarial_flip(
            case,
            view,
            invariant_id=plan.invariant_id,
            replacement_value=plan.replacement_value,
        )
    raise AssertionError(f"Unhandled mutation kind: {plan.kind}")


def _trial_id(case: CanonicalCase, representation: Representation, plan: MutationPlan) -> str:
    target = plan.invariant_id or "all"
    return f"{case.scenario_id}:{representation.value}:{plan.kind.value}:{target}:{plan.stable_key()}"


def _equivalence_group(case: CanonicalCase, plan: MutationPlan) -> str:
    target = plan.invariant_id or "all"
    return f"{case.scenario_id}:{plan.kind.value}:{target}:{plan.stable_key()}"


def generate_trial(
    case: CanonicalCase,
    representation: Representation | str,
    mutation: MutationPlan | None = None,
    *,
    policy: EvaluationPolicy | None = None,
) -> GeneratedTrial:
    plan = mutation or MutationPlan()
    rep = Representation(representation)
    expectation = derive_trial_expectation(case, plan, policy)
    view = apply_mutation(case, build_evidence_view(case), plan)
    artifact = RENDERERS[rep.value](case, view)
    return GeneratedTrial(
        trial_id=_trial_id(case, rep, plan),
        equivalence_group=_equivalence_group(case, plan),
        scenario_id=case.scenario_id,
        representation=rep,
        mutation=plan,
        expectation=expectation,
        artifact=artifact,
    )


def generate_trial_matrix(
    cases: Iterable[CanonicalCase],
    representations: Iterable[Representation | str],
    mutation_plans: Iterable[MutationPlan],
    *,
    policies: dict[str, EvaluationPolicy] | None = None,
) -> tuple[GeneratedTrial, ...]:
    """Generate the deterministic cartesial trial matrix.

    Mutation plans are expected to be valid for every case supplied. Suite-level
    code can therefore use one matrix for shared plans or call this function per
    scenario for target-specific plans.
    """

    cases_tuple = tuple(cases)
    reps_tuple = tuple(Representation(item) for item in representations)
    plans_tuple = tuple(mutation_plans)
    policies = policies or {}
    return tuple(
        generate_trial(
            case,
            rep,
            plan,
            policy=policies.get(case.scenario_id),
        )
        for case, rep, plan in product(cases_tuple, reps_tuple, plans_tuple)
    )
