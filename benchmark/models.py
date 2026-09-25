"""Frozen canonical data model for UNISON-StateBench v0.1.

The model layer encodes the constitutional invariant:

    I_k = (value, epistemic_status, provenance, authority)

Canonical structures are deeply immutable: mutable mappings are normalized into
sorted tuples of frozen records during validation.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


JsonScalar: TypeAlias = bool | int | float | str | None


class FrozenModel(BaseModel):
    """Base class for immutable, deterministic canonical models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class EpistemicStatus(str, Enum):
    """Epistemic state for a canonical or observed invariant."""

    KNOWN = "known"
    UNKNOWN = "unknown"
    ABSENT = "absent"
    CONFLICT = "conflict"


class CanonicalStateEntry(FrozenModel):
    key: str
    value: JsonScalar


class SourceRecord(FrozenModel):
    id: str
    authority_rank: Annotated[int, Field(ge=0)]
    trusted: bool
    kind: str = "record"
    description: str | None = None
    source_derived: bool = False


class AuthorityBinding(FrozenModel):
    """Binds an invariant to the source authorized to establish it."""

    source_id: str
    minimum_rank: Annotated[int, Field(ge=0)] = 0
    trusted_required: bool = True


class EvidenceRecord(FrozenModel):
    """Evidence that may authorize a state transition."""

    id: str
    source_id: str
    present: bool = True
    supports_transition: bool = True
    description: str | None = None


class CanonicalInvariant(FrozenModel):
    id: str
    value: JsonScalar
    epistemic_status: EpistemicStatus
    provenance: tuple[str, ...] = ()
    authority: AuthorityBinding
    required: bool = True
    description: str | None = None

    @model_validator(mode="after")
    def validate_epistemic_value(self) -> "CanonicalInvariant":
        if self.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            if self.value is not None:
                raise ValueError(
                    f"Invariant {self.id}: {self.epistemic_status.value} requires value=None"
                )
        if self.epistemic_status is EpistemicStatus.KNOWN and self.value is None:
            raise ValueError(f"Invariant {self.id}: known invariant requires a value")
        return self

    def tuple4(self) -> tuple[JsonScalar, EpistemicStatus, tuple[str, ...], AuthorityBinding]:
        return (self.value, self.epistemic_status, self.provenance, self.authority)


class TransitionRequirement(FrozenModel):
    """A required boundary between distinct workflow states."""

    id: str
    from_invariant: str
    to_invariant: str
    required_evidence: tuple[str, ...] = ()
    observed: bool = False
    minimum_authority_rank: Annotated[int, Field(ge=0)] = 0
    description: str | None = None


class RuleCondition(FrozenModel):
    invariant_id: str
    value: JsonScalar = None
    epistemic_status: EpistemicStatus | None = None


class DecisionRule(FrozenModel):
    """Declarative deterministic decision rule, evaluated in priority order."""

    id: str
    priority: int = 100
    conditions: tuple[RuleCondition, ...]
    decision: str
    authorized_actions: tuple[str, ...] = ()


class CanonicalCase(FrozenModel):
    schema_version: Literal["unison.case.v1"] = "unison.case.v1"
    scenario_id: str
    domain: str
    title: str
    canonical_state: tuple[CanonicalStateEntry, ...]
    invariants: tuple[CanonicalInvariant, ...]
    sources: tuple[SourceRecord, ...]
    evidence: tuple[EvidenceRecord, ...] = ()
    transitions: tuple[TransitionRequirement, ...] = ()
    decision_rules: tuple[DecisionRule, ...]
    notes: tuple[str, ...] = ()

    @field_validator("canonical_state", mode="before")
    @classmethod
    def freeze_canonical_state(cls, value):
        if isinstance(value, dict):
            return tuple({"key": key, "value": value[key]} for key in sorted(value))
        return value

    @model_validator(mode="after")
    def validate_references(self) -> "CanonicalCase":
        state_keys = {entry.key for entry in self.canonical_state}
        if len(state_keys) != len(self.canonical_state):
            raise ValueError("Canonical state keys must be unique")

        invariant_ids = {i.id for i in self.invariants}
        if len(invariant_ids) != len(self.invariants):
            raise ValueError("Invariant IDs must be unique")

        source_ids = {s.id for s in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("Source IDs must be unique")

        evidence_ids = {e.id for e in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            raise ValueError("Evidence IDs must be unique")

        for invariant in self.invariants:
            authority_source = source_ids and invariant.authority.source_id
            if authority_source not in source_ids:
                raise ValueError(
                    f"Invariant {invariant.id} authority source "
                    f"{invariant.authority.source_id!r} not declared"
                )
            source = self.source_map()[invariant.authority.source_id]
            if source.authority_rank < invariant.authority.minimum_rank:
                raise ValueError(
                    f"Invariant {invariant.id} requires authority rank "
                    f">={invariant.authority.minimum_rank}, got {source.authority_rank}"
                )
            if invariant.authority.trusted_required and not source.trusted:
                raise ValueError(
                    f"Invariant {invariant.id} requires a trusted authority source"
                )
            missing_provenance = set(invariant.provenance) - source_ids
            if missing_provenance:
                raise ValueError(
                    f"Invariant {invariant.id} references unknown provenance sources: "
                    f"{sorted(missing_provenance)}"
                )

        for item in self.evidence:
            if item.source_id not in source_ids:
                raise ValueError(f"Evidence {item.id} references unknown source {item.source_id}")

        for transition in self.transitions:
            if transition.from_invariant not in invariant_ids:
                raise ValueError(
                    f"Transition {transition.id} has unknown from_invariant "
                    f"{transition.from_invariant}"
                )
            if transition.to_invariant not in invariant_ids:
                raise ValueError(
                    f"Transition {transition.id} has unknown to_invariant "
                    f"{transition.to_invariant}"
                )
            missing_evidence = set(transition.required_evidence) - evidence_ids
            if missing_evidence:
                raise ValueError(
                    f"Transition {transition.id} references unknown evidence: "
                    f"{sorted(missing_evidence)}"
                )

        for rule in self.decision_rules:
            for condition in rule.conditions:
                if condition.invariant_id not in invariant_ids:
                    raise ValueError(
                        f"Decision rule {rule.id} references unknown invariant "
                        f"{condition.invariant_id}"
                    )
        return self

    def canonical_state_map(self) -> dict[str, JsonScalar]:
        """Return a detached mutable view, never the canonical storage."""
        return {entry.key: entry.value for entry in self.canonical_state}

    def invariant_map(self) -> dict[str, CanonicalInvariant]:
        return {item.id: item for item in self.invariants}

    def source_map(self) -> dict[str, SourceRecord]:
        return {item.id: item for item in self.sources}

    def evidence_map(self) -> dict[str, EvidenceRecord]:
        return {item.id: item for item in self.evidence}


class OracleInvariant(FrozenModel):
    id: str
    value: JsonScalar
    epistemic_status: EpistemicStatus
    provenance: tuple[str, ...]
    authority: AuthorityBinding


class OracleTransitionState(FrozenModel):
    id: str
    satisfied: bool


class OracleResult(FrozenModel):
    scenario_id: str
    invariants: tuple[OracleInvariant, ...]
    decision: str
    authorized_actions: tuple[str, ...] = ()
    transitions: tuple[OracleTransitionState, ...] = ()

    def invariant_map(self) -> dict[str, OracleInvariant]:
        return {item.id: item for item in self.invariants}

    def transition_map(self) -> dict[str, bool]:
        return {item.id: item.satisfied for item in self.transitions}


class InvariantObservation(FrozenModel):
    id: str
    value: JsonScalar
    epistemic_status: EpistemicStatus
    provenance: tuple[str, ...] = ()
    authority_source: str | None = None

    @model_validator(mode="after")
    def validate_epistemic_value(self) -> "InvariantObservation":
        if self.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            if self.value is not None:
                raise ValueError(
                    f"Observation {self.id}: {self.epistemic_status.value} requires value=None"
                )
        if self.epistemic_status is EpistemicStatus.KNOWN and self.value is None:
            raise ValueError(f"Observation {self.id}: known observation requires a value")
        return self


class StructuredObservation(FrozenModel):
    scenario_id: str
    invariants: tuple[InvariantObservation, ...]
    contradiction_detected: ibool = False
    insufficient_evidence: bool = False
    decision: str
    authorized_actions: tuple[str, ...] = ()
    explanation: str | None = None

    def invariant_map(self) -> dict[str, InvariantObservation]:
        return {item.id: item for item in self.invariants}
