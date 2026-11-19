"""Typed non-collapse models and runtime for the post-v0.1 extension."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import Field, model_validator

from .models import EpistemicStatus, FrozenModel


class RelationType(str, Enum):
    INVARIANT_EQUIVALENCE = "invariant_equivalence"
    APPROX_INVARIANT_EQUIVALENCE = "approx_invariant_equivalence"
    STATE_PROXIMITY = "state_proximity"
    TRANSFORMATION_EDGE = "transformation_edge"
    ORBIT_MEMBERSHIP = "orbit_membership"
    REACHABILITY = "reachability"
    ANTAGONISM = "antagonism"
    STATISTICAL_COUPLING = "statistical_coupling"
    BASELINE_VIABILITY = "baseline_viability"
    ROBUST_VIABILITY = "robust_viability"


class CertificateKind(str, Enum):
    INVARIANT = "C_I"
    EQUIVARIANCE = "C_Q"
    ROBUSTNESS = "C_R"
    VIABILITY = "C_V"
    OCCUPANCY_ASYMMETRY = "C_A"
    ANTAGONISTIC_ABSORPTION = "C_ANTAGONISM"


class CertificateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class BridgeFamily(str, Enum):
    RELATION = "relation"
    CERTIFICATE = "certificate"
    BOUNDARY = "boundary"


class RelationFact(FrozenModel):
    id: str
    relation_type: RelationType
    subject: str
    object: str
    value: bool | None
    epistemic_status: EpistemicStatus
    metric: str | None = None
    epsilon: float | None = None
    horizon: str | float | None = None
    process_signature: str | None = None
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> "RelationFact":
        _validate_epistemic(self.value, self.epistemic_status, "relation")
        if self.relation_type is RelationType.REACHABILITY and (
            self.horizon is None or not self.process_signature
        ):
            raise ValueError("reachability requires both horizon and process_signature")
        return self


class RelationObservation(FrozenModel):
    id: str
    value: bool | None
    epistemic_status: EpistemicStatus

    @model_validator(mode="after")
    def validate_shape(self) -> "RelationObservation":
        _validate_epistemic(self.value, self.epistemic_status, "relation observation")
        return self


class CertificateResult(FrozenModel):
    kind: CertificateKind
    status: CertificateStatus
    raw_value: bool | float | str | None = None
    threshold: float | None = None
    evidence_ids: tuple[str, ...] = ()
    reason: str | None = None


class CertificateVector(FrozenModel):
    certificates: tuple[CertificateResult, ...] = ()

    @model_validator(mode="after")
    def unique_kinds(self) -> "CertificateVector":
        kinds = [item.kind for item in self.certificates]
        if len(kinds) != len(set(kinds)):
            raise ValueError("certificate kinds must be unique")
        return self

    def certificate_map(self) -> dict[CertificateKind, CertificateResult]:
        return {item.kind: item for item in self.certificates}


class FixtureParameter(FrozenModel):
    id: str
    value: bool | int | float | str | None


class FixtureClaim(FrozenModel):
    id: str
    value: bool | None
    epistemic_status: EpistemicStatus
    reason_code: str
    diagnostic_code: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "FixtureClaim":
        _validate_epistemic(self.value, self.epistemic_status, "claim")
        return self


class ClaimObservation(FrozenModel):
    id: str
    value: bool | None
    epistemic_status: EpistemicStatus

    @model_validator(mode="after")
    def validate_shape(self) -> "ClaimObservation":
        _validate_epistemic(self.value, self.epistemic_status, "claim observation")
        return self


def _validate_epistemic(value: bool | None, status: EpistemicStatus, label: str) -> None:
    if status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT} and value is not None:
        raise ValueError(f"unknown/absent {label} requires value=None")
    if status is EpistemicStatus.KNOWN and value is None:
        raise ValueError(f"known {label} requires a boolean value")


class RelationBridgeRequirement(FrozenModel):
    id: str
    source_relation_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    target_relation_id: str
    required_evidence_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    obstruction_evidence_ids: tuple[str, ...] = ()
    diagnostic_code: str
    family: BridgeFamily = BridgeFamily.RELATION


class CertificateBridgeRequirement(FrozenModel):
    id: str
    source_kind: CertificateKind
    source_status: CertificateStatus
    target_kind: CertificateKind
    target_status: CertificateStatus
    required_evidence_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    diagnostic_code: str
    family: BridgeFamily = BridgeFamily.CERTIFICATE

    @model_validator(mode="after")
    def distinct_endpoints(self) -> "CertificateBridgeRequirement":
        if self.source_kind is self.target_kind:
            raise ValueError("certificate bridge must connect distinct certificate kinds")
        return self


class TypedFixture(FrozenModel):
    schema_version: str = "unison.typed-noncollapse.v1"
    scenario_id: str
    relations: Annotated[tuple[RelationFact, ...], Field(min_length=1)]
    relation_bridges: tuple[RelationBridgeRequirement, ...] = ()
    certificate_vector: CertificateVector = CertificateVector()
    certificate_bridges: tuple[CertificateBridgeRequirement, ...] = ()
    claims: tuple[FixtureClaim, ...] = ()
    parameters: tuple[FixtureParameter, ...] = ()
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_refs(self) -> "TypedFixture":
        relation_ids = [item.id for item in self.relations]
        _require_unique(relation_ids, "relation")
        relation_set = set(relation_ids)
        bridge_ids = [b.id for b in self.relation_bridges] + [b.id for b in self.certificate_bridges]
        _require_unique(bridge_ids, "bridge")
        for bridge in self.relation_bridges:
            refs = set(bridge.source_relation_ids) | {bridge.target_relation_id}
            missing = refs - relation_set
            if missing:
                raise ValueError(f"bridge {bridge.id} references unknown relations: {sorted(missing)}")
            if bridge.target_relation_id in bridge.source_relation_ids:
                raise ValueError("relation bridge target cannot also be a source")
        certs = set(self.certificate_vector.certificate_map())
        for bridge in self.certificate_bridges:
            missing = {bridge.source_kind, bridge.target_kind} - certs
            if missing:
                raise ValueError(f"certificate bridge {bridge.id} references missing certificate kinds")
        _require_unique([item.id for item in self.claims], "claim")
        _require_unique([item.id for item in self.parameters], "parameter")
        return self

    def relation_map(self) -> dict[str, RelationFact]:
        return {item.id: item for item in self.relations}

    def claim_map(self) -> dict[str, FixtureClaim]:
        return {item.id: item for item in self.claims}

    def parameter_map(self) -> dict[str, FixtureParameter]:
        return {item.id: item for item in self.parameters}


def _require_unique(items: list[str], label: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{label} IDs must be unique")


class TypedObservation(FrozenModel):
    scenario_id: str
    relations: tuple[RelationObservation, ...] = ()
    certificate_vector: CertificateVector = CertificateVector()
    claims: tuple[ClaimObservation, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def relation_map(self) -> dict[str, RelationObservation]:
        return {item.id: item for item in self.relations}

    def claim_map(self) -> dict[str, ClaimObservation]:
        return {item.id: item for item in self.claims}


class TypedOracleResult(FrozenModel):
    scenario_id: str
    relations: tuple[RelationFact, ...]
    certificate_vector: CertificateVector
    claims: tuple[FixtureClaim, ...] = ()
    parameters: tuple[FixtureParameter, ...] = ()

    def relation_map(self) -> dict[str, RelationFact]:
        return {item.id: item for item in self.relations}

    def claim_map(self) -> dict[str, FixtureClaim]:
        return {item.id: item for item in self.claims}

    def parameter_map(self) -> dict[str, FixtureParameter]:
        return {item.id: item for item in self.parameters}


def load_typed_fixture(path: str | Path) -> TypedFixture:
    return TypedFixture.model_validate_json(Path(path).read_text(encoding="utf-8"))


def derive_typed_oracle(fixture) -> TypedOracleResult:
    if not isinstance(fixture, TypedFixture):
        fixture = TypedFixture.model_validate(fixture)
    return TypedOracleResult(
        scenario_id=fixture.scenario_id,
        relations=fixture.relations,
        certificate_vector=fixture.certificate_vector,
        claims=fixture.claims,
        parameters=fixture.parameters,
    )


class TypedCollapseKind(str, Enum):
    RELATION_SUBSTITUTION = "relation_substitution"
    CERTIFICATE_SUBSTITUTION = "certificate_substitution"
    BOUNDARY_SUBSTITUTION = "boundary_substitution"
    UNKNOWN_TO_KNOWN = "unknown_to_known"


class TypedStateCollapse(FrozenModel):
    kind: TypedCollapseKind
    subject_id: str
    boundary_id: str
    diagnostic_code: str
    message: str


class TypedStateCollapseReport(FrozenModel):
    scenario_id: str
    boundary_trials: Annotated[int, Field(ge=0)]
    collapses: tuple[TypedStateCollapse, ...] = ()

    @property
    def count(self) -> int:
        return len(self.collapses)

    @property
    def rate(self) -> float:
        return 0.0 if self.boundary_trials == 0 else min(1.0, self.count / self.boundary_trials)

    def to_state_collapse_report(self):
        """Project typed diagnostics into the frozen SCR counting interface."""
        from .state_collapse import CollapseKind, StateCollapse, StateCollapseReport

        collapses = tuple(
            StateCollapse(
                kind=(CollapseKind.UNKNOWN_TO_KNOWN if item.kind is TypedCollapseKind.UNKNOWN_TO_KNOWN
                      else CollapseKind.UNSUPPORTED_TRANSITION),
                invariant_id=f"TYPED:{item.subject_id}",
                boundary_id=item.boundary_id,
                message=f"[{item.diagnostic_code}] {item.message}",
            )
            for item in self.collapses
        )
        return StateCollapseReport(
            scenario_id=self.scenario_id,
            boundary_trials=self.boundary_trials,
            collapses=collapses,
        )


def _collapse_kind(family: BridgeFamily) -> TypedCollapseKind:
    if family is BridgeFamily.RELATION:
        return TypedCollapseKind.RELATION_SUBSTITUTION
    if family is BridgeFamily.BOUNDARY:
        return TypedCollapseKind.BOUNDARY_SUBSTITUTION
    return TypedCollapseKind.CERTIFICATE_SUBSTITUTION


def detect_typed_state_collapses(fixture, observation) -> TypedStateCollapseReport:
    if not isinstance(fixture, TypedFixture):
        fixture = TypedFixture.model_validate(fixture)
    if not isinstance(observation, TypedObservation):
        observation = TypedObservation.model_validate(observation)
    if observation.scenario_id != fixture.scenario_id:
        raise ValueError("Observation scenario_id does not match typed fixture")

    oracle = derive_typed_oracle(fixture)
    expected_rel = oracle.relation_map()
    observed_rel = observation.relation_map()
    expected_cert = oracle.certificate_vector.certificate_map()
    observed_cert = observation.certificate_vector.certificate_map()
    observed_claims = observation.claim_map()
    evidence = set(observation.evidence_ids)
    collapses: list[TypedStateCollapse] = []

    for bridge in fixture.relation_bridges:
        target = observed_rel.get(bridge.target_relation_id)
        if target is None or target.epistemic_status is not EpistemicStatus.KNOWN or target.value is not True:
            continue
        sources_hold = all(
            expected_rel[source].epistemic_status is EpistemicStatus.KNOWN
            and expected_rel[source].value is True
            for source in bridge.source_relation_ids
        )
        canonical_target = expected_rel[bridge.target_relation_id]
        canonical_true = canonical_target.epistemic_status is EpistemicStatus.KNOWN and canonical_target.value is True
        bridge_present = set(bridge.required_evidence_ids).issubset(evidence)
        if sources_hold and not canonical_true and not bridge_present:
            collapses.append(TypedStateCollapse(
                kind=_collapse_kind(bridge.family),
                subject_id=bridge.target_relation_id,
                boundary_id=bridge.id,
                diagnostic_code=bridge.diagnostic_code,
                message=f"Observed {bridge.target_relation_id}=true without required bridge evidence.",
            ))

    for bridge in fixture.certificate_bridges:
        source = expected_cert.get(bridge.source_kind)
        canonical_target = expected_cert.get(bridge.target_kind)
        target = observed_cert.get(bridge.target_kind)
        if source is None or canonical_target is None or target is None:
            continue
        bridge_present = set(bridge.required_evidence_ids).issubset(evidence)
        if (source.status is bridge.source_status
                and target.status is bridge.target_status
                and canonical_target.status is not bridge.target_status
                and not bridge_present):
            collapses.append(TypedStateCollapse(
                kind=_collapse_kind(bridge.family),
                subject_id=bridge.target_kind.value,
                boundary_id=bridge.id,
                diagnostic_code=bridge.diagnostic_code,
                message=f"Observed {bridge.target_kind.value}={bridge.target_status.value} without required bridge evidence.",
            ))

    epistemic_trials = 0
    for claim in oracle.claims:
        if claim.epistemic_status not in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            continue
        epistemic_trials += 1
        observed = observed_claims.get(claim.id)
        if observed is not None and observed.epistemic_status is EpistemicStatus.KNOWN:
            collapses.append(TypedStateCollapse(
                kind=TypedCollapseKind.UNKNOWN_TO_KNOWN,
                subject_id=claim.id,
                boundary_id=f"EPISTEMIC:{claim.id}",
                diagnostic_code=claim.diagnostic_code or "EPISTEMIC.UNKNOWN_TO_KNOWN",
                message=f"Observed known {claim.id} although justified status is {claim.epistemic_status.value}.",
            ))

    return TypedStateCollapseReport(
        scenario_id=fixture.scenario_id,
        boundary_trials=len(fixture.relation_bridges) + len(fixture.certificate_bridges) + epistemic_trials,
        collapses=tuple(collapses),
    )
