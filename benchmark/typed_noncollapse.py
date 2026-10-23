"""Typed relation and certificate models for the post-v0.1 non-collapse extension."""
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
    def validate_relation(self) -> "RelationFact":
        if self.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            if self.value is not None:
                raise ValueError("unknown/absent relation requires value=None")
        if self.epistemic_status is EpistemicStatus.KNOWN and self.value is None:
            raise ValueError("known relation requires a boolean value")
        if self.relation_type is RelationType.REACHABILITY:
            if self.horizon is None or not self.process_signature:
                raise ValueError("reachability requires both horizon and process_signature")
        return self


class RelationObservation(FrozenModel):
    id: str
    value: bool | None
    epistemic_status: EpistemicStatus

    @model_validator(mode="after")
    def validate_relation(self) -> "RelationObservation":
        if self.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            if self.value is not None:
                raise ValueError("unknown/absent relation observation requires value=None")
        if self.epistemic_status is EpistemicStatus.KNOWN and self.value is None:
            raise ValueError("known relation observation requires a boolean value")
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
    def validate_claim(self) -> "FixtureClaim":
        if self.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            if self.value is not None:
                raise ValueError("unknown/absent claim requires value=None")
        if self.epistemic_status is EpistemicStatus.KNOWN and self.value is None:
            raise ValueError("known claim requires a boolean value")
        return self


class ClaimObservation(FrozenModel):
    id: str
    value: bool | None
    epistemic_status: EpistemicStatus

    @model_validator(mode="after")
    def validate_claim(self) -> "ClaimObservation":
        if self.epistemic_status in {EpistemicStatus.UNKNOWN, EpistemicStatus.ABSENT}:
            if self.value is not None:
                raise ValueError("unknown/absent claim observation requires value=None")
        if self.epistemic_status is EpistemicStatus.KNOWN and self.value is None:
            raise ValueError("known claim observation requires a boolean value")
        return self


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
    def validate_references(self) -> "TypedFixture":
        relation_ids = [item.id for item in self.relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("relation IDs must be unique")
        relation_id_set = set(relation_ids)

        bridge_ids = [item.id for item in self.relation_bridges] + [
            item.id for item in self.certificate_bridges
        ]
        if len(bridge_ids) != len(set(bridge_ids)):
            raise ValueError("bridge IDs must be unique")

        for bridge in self.relation_bridges:
            missing = set(bridge.source_relation_ids) - relation_id_set
            if bridge.target_relation_id not in relation_id_set:
                missing.add(bridge.target_relation_id)
            if missing:
                raise ValueError(f"bridge {bridge.id} references unknown relations: {sorted(missing)}")
            if bridge.target_relation_id in bridge.source_relation_ids:
                raise ValueError("relation bridge target cannot also be a source")

        certificate_kinds = set(self.certificate_vector.certificate_map())
        for bridge in self.certificate_bridges:
            missing = {bridge.source_kind, bridge.target_kind} - certificate_kinds
            if missing:
                raise ValueError(
                    f"certificate bridge {bridge.id} references missing certificate kinds: "
                    f"{sorted(item.value for item in missing)}"
                )

        claim_ids = [item.id for item in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim IDs must be unique")
        parameter_ids = [item.id for item in self.parameters]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("parameter IDs must be unique")
        return self

    def relation_map(self) -> dict[str, RelationFact]:
        return {item.id: item for item in self.relations}

    def claim_map(self) -> dict[str, FixtureClaim]:
        return {item.id: item for item in self.claims}

    def parameter_map(self) -> dict[str, FixtureParameter]:
        return {item.id: item for item in self.parameters}


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

    def relation_map(self) -> dict[str, RelationFact]:
        return {item.id: item for item in self.relations}

    def claim_map(self) -> dict[str, FixtureClaim]:
        return {item.id: item for item in self.claims}

    def parameter_map(self) -> dict[str, FixtureParameter]:
        return {item.id: item for item in self.parameters}


def load_typed_fixture(path: str | Path) -> TypedFixture:
    """Load and validate a typed non-collapse fixture from JSON."""
    return TypedFixture.model_validate_json(Path(path).read_text(encoding="utf-8"))
