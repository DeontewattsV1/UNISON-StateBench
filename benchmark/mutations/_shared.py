"""Shared mutation helpers."""

from __future__ import annotations

from ..models import CanonicalCase, JsonScalar
from ..presentation import EvidenceView, MutationTrace, PresentedClaim, assert_view_origin


def require_view(case: CanonicalCase, view: EvidenceView) -> EvidenceView:
    assert_view_origin(case, view)
    return view


def canonical_claim(view: EvidenceView, invariant_id: str) -> tuple[int, PresentedClaim]:
    for index, claim in enumerate(view.claims):
        if claim.invariant_id == invariant_id and not claim.injected:
            return index, claim
    raise KeyError(f"No canonical presentation claim for invariant {invariant_id!r}")


def source_for(case: CanonicalCase, source_id: str):
    try:
        return case.source_map()[source_id]
    except KeyError as exc:
        raise KeyError(f"Unknown source {source_id!r}") from exc


def default_low_authority_source(case: CanonicalCase, invariant_id: str):
    invariant = case.invariant_map()[invariant_id]
    authority = case.source_map()[invariant.authority.source_id]
    candidates = [
        item
        for item in case.sources
        if item.id != authority.id and item.authority_rank < authority.authority_rank
    ]
    if not candidates:
        raise ValueError(
            f"No lower-authority source available for invariant {invariant_id!r}"
        )
    # Prefer explicitly untrusted, then lowest rank, then stable source id.
    return sorted(candidates, key=lambda item: (item.trusted, item.authority_rank, item.id))[0]


def flipped_value(value: JsonScalar) -> JsonScalar:
    if isinstance(value, bool):
        return not value
    if value is None:
        return "asserted"
    if isinstance(value, str):
        return f"NOT_{value}"
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    raise TypeError(f"Cannot deterministically flip value of type {type(value).__name__}")


def append_trace(view: EvidenceView, trace: MutationTrace, **updates) -> EvidenceView:
    return view.model_copy(
        update={
            **updates,
            "mutation_trace": view.mutation_trace + (trace,),
        }
    )
