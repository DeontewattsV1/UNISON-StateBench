"""Invariant Preservation Rate (IPR)."""

from __future__ import annotations

from pydantic import Field

from ..models import FrozenModel, StructuredObservation
from ..trials import TrialExpectation


class InvariantPreservationDetail(FrozenModel):
    invariant_id: str
    value_preserved: bool
    epistemic_preserved: bool
    provenance_preserved: bool
    authority_preserved: bool

    @property
    def fully_preserved(self) -> bool:
        return (
            self.value_preserved
            and self.epistemic_preserved
            and self.provenance_preserved
            and self.authority_preserved
        )


class InvariantPreservationResult(FrozenModel):
    preserved: int = Field(ge=0)
    tested: int = Field(ge=0)
    details: tuple[InvariantPreservationDetail, ...] = ()


def score_invariant_preservation(
    expectation: TrialExpectation,
    observation: StructuredObservation,
) -> InvariantPreservationResult:
    observed = observation.invariant_map()
    details: list[InvariantPreservationDetail] = []
    for expected in expectation.invariants:
        if not expected.required:
            continue
        actual = observed.get(expected.id)
        if actual is None:
            details.append(
                InvariantPreservationDetail(
                    invariant_id=expected.id,
                    value_preserved=False,
                    epistemic_preserved=False,
                    provenance_preserved=False,
                    authority_preserved=False,
                )
            )
            continue
        details.append(
            InvariantPreservationDetail(
                invariant_id=expected.id,
                value_preserved=actual.value == expected.value,
                epistemic_preserved=actual.epistemic_status is expected.epistemic_status,
                provenance_preserved=set(actual.provenance) == set(expected.provenance),
                authority_preserved=actual.authority_source == expected.authority_source,
            )
        )
    return InvariantPreservationResult(
        preserved=sum(item.fully_preserved for item in details),
        tested=len(details),
        details=tuple(details),
    )
