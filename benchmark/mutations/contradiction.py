"""Inject an explicit conflicting claim without rewriting canonical truth."""

from __future__ import annotations

from ..models import CanonicalCase, EpistemicStatus, JsonScalar
from ..presentation import EvidenceView, MutationTrace, PresentedClaim
from ..transform_guard import integrity_guarded
from ._shared import (
    append_trace,
    canonical_claim,
    default_low_authority_source,
    flipped_value,
    require_view,
    source_for,
)


@integrity_guarded
def inject_contradiction(
    case: CanonicalCase,
    view: EvidenceView,
    *,
    invariant_id: str,
    source_id: str | None = None,
    conflicting_value: JsonScalar | None = None,
) -> EvidenceView:
    view = require_view(case, view)
    _, canonical = canonical_claim(view, invariant_id)
    source = (
        default_low_authority_source(case, invariant_id)
        if source_id is None
        else source_for(case, source_id)
    )
    value = flipped_value(canonical.value) if conflicting_value is None else conflicting_value
    if value == canonical.value:
        raise ValueError("Contradiction value must differ from the canonical presented value")
    injected = PresentedClaim(
        id=f"MUT:CONTRADICTION:{invariant_id}:{source.id}",
        invariant_id=invariant_id,
        value=value,
        epistemic_status=EpistemicStatus.KNOWN,
        source_id=source.id,
        authority_rank=source.authority_rank,
        trusted=source.trusted,
        provenance=(source.id,),
        description="Injected conflicting presentation claim.",
        injected=True,
    )
    return append_trace(
        view,
        MutationTrace(
            kind="contradiction",
            target=invariant_id,
            details=(f"source={source.id}", f"value={value!r}"),
        ),
        claims=view.claims + (injected,),
    )
