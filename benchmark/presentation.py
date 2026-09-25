"""Immutable evidence views and rendered artifacts for UNISON-StateBench v0.1.

CanonicalCase remains the reference truth. Presentation objects are detached,
immutable views that may be reordered, paraphrased, hidden, contradicted, or
adversarially modified without rewriting the canonical case or oracle.
"""

from __future__ import annotations

from typing import Literal

from .integrity import IntegritySnapshot, snapshot
from .models import (
    CanonicalCase,
    EpistemicStatus,
    EvidenceRecord,
    FrozenModel,
    JsonScalar,
    SourceRecord,
    TransitionRequirement,
)
from .transform_guard import integrity_guarded


class PresentedClaim(FrozenModel):
    """A presentation-layer claim about one canonical invariant."""

    id: str
    invariant_id: str
    value: JsonScalar
    epistemic_status: EpistemicStatus
    source_id: str
    authority_rank: int
    trusted: bool
    provenance: tuple[str, ...] = ()
    description: str | None = None
    injected: bool = False


class MutationTrace(FrozenModel):
    """Auditable description of a presentation-only transformation."""

    kind: str
    target: str | None = None
    details: tuple[str, ...] = ()


class EvidenceView(FrozenModel):
    """Detached evidence surface presented to a model.

    The origin digests bind the view to exactly one canonical case + oracle.
    Mutations preserve these digests; they never become a new source of truth.
    """

    scenario_id: str
    domain: str
    title: str
    claims: tuple[PresentedClaim, ...]
    sources: tuple[SourceRecord, ...]
    evidence: tuple[EvidenceRecord, ...] = ()
    transitions: tuple[TransitionRequirement, ...] = ()
    notes: tuple[str, ...] = ()
    mutation_trace: tuple[MutationTrace, ...] = ()
    origin_case_digest: str
    origin_oracle_digest: str

    def claim_map(self) -> dict[str, tuple[PresentedClaim, ...]]:
        grouped: dict[str, list[PresentedClaim]] = {}
        for claim in self.claims:
            grouped.setdefault(claim.invariant_id, []).append(claim)
        return {key: tuple(value) for key, value in grouped.items()}


class RenderedArtifact(FrozenModel):
    scenario_id: str
    format: Literal["prose", "json", "yaml", "table", "event_log"]
    content: str
    origin_case_digest: str
    origin_oracle_digest: str
    mutation_trace: tuple[MutationTrace, ...] = ()


def _assert_origin_snapshot(view: EvidenceView, snap: IntegritySnapshot) -> None:
    if view.origin_case_digest != snap.case_digest:
        raise ValueError("EvidenceView does not belong to the supplied canonical case")
    if view.origin_oracle_digest != snap.oracle_digest:
        raise ValueError("EvidenceView oracle digest does not match the supplied canonical case")


def assert_view_origin(case: CanonicalCase, view: EvidenceView) -> None:
    """Reject cross-case/cross-oracle evidence views."""
    if view.scenario_id != case.scenario_id:
        raise ValueError("EvidenceView scenario_id does not match canonical case")
    _assert_origin_snapshot(view, snapshot(case))


@integrity_guarded
def build_evidence_view(case: CanonicalCase) -> EvidenceView:
    """Build the deterministic, detached baseline presentation view."""
    snap = snapshot(case)
    source_map = case.source_map()
    claims: list[PresentedClaim] = []
    for invariant in case.invariants:
        authority_source = source_map[invariant.authority.source_id]
        claims.append(
            PresentedClaim(
                id=f"CLAIM:{invariant.id}:CANONICAL",
                invariant_id=invariant.id,
                value=invariant.value,
                epistemic_status=invariant.epistemic_status,
                source_id=authority_source.id,
                authority_rank=authority_source.authority_rank,
                trusted=authority_source.trusted,
                provenance=invariant.provenance,
                description=invariant.description,
                injected=False,
            )
        )

    return EvidenceView(
        scenario_id=case.scenario_id,
        domain=case.domain,
        title=case.title,
        claims=tuple(claims),
        sources=case.sources,
        evidence=case.evidence,
        transitions=case.transitions,
        notes=case.notes,
        origin_case_digest=snap.case_digest,
        origin_oracle_digest=snap.oracle_digest,
    )


def ensure_view(case: CanonicalCase, view: EvidenceView | None) -> EvidenceView:
    """Return a verified view, building the baseline when omitted."""
    resolved = build_evidence_view(case) if view is None else view
    assert_view_origin(case, resolved)
    return resolved
