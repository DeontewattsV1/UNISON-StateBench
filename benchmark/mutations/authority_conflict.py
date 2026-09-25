"""Inject a lower-authority claim that conflicts with the authoritative claim."""

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
def inject_authority_conflict(
    case: CanonicalCase,
    view: EvidenceView,
    *,
    invariant_id: str,
    lower_source_id: str | None = None,
    conflicting_value: JsonScalar | None = None,
) -> EvidenceView:
    view = require_view(case, view)
    _, canonical = canonical_claim(view, invariant_id)
    authoritative = case.source_map()[case.invariant_map()[invariant_id].authority.source_id]
    lower = (
        default_low_authority_source(case, invariant_id)
        if lower_source_id is None
        else source_for(case, lower_source_id)
    )
    if lower.authority_rank >= authoritative.authority_rank:
        raise ValueError("Authority-conflict source must rank below canonical authority")
    value = flipped_value(canonical.value) if conflicting_value is None else conflicting_value
    if value == canonical.value:
        raise ValueError("Authority-conflict value must differ from canonical value")
    claim = PresentedClaim(
        id=f"MUT:AUTHORITY_CONFLICT:{invariant_id}:{lower.id}",
        invariant_id=invariant_id,
        value=value,
        epistemic_status=EpistemicStatus.KNOWN,
        source_id=lower.id,
        authority_rank=lower.authority_rank,
        trusted=lower.trusted,
        provenance=(lower.id,),
        description=(
            f"Lower-authority claim conflicts with authoritative source {authoritative.id}."
        ),
        injected=True,
    )
    return append_trace(
        view,
        MutationTrace(
            kind="authority_conflict",
            target=invariant_id,
            details=(
                f"authoritative_source={authoritative.id}",
                f"conflicting_source={lower.id}",
                f"value={value!r}",
            ),
        ),
        claims=view.claims + (claim,),
    )
