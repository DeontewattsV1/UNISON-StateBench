"""Remove presentation evidence for one invariant."""

from __future__ import annotations

from ..models import CanonicalCase
from ..presentation import EvidenceView, MutationTrace
from ..transform_guard import integrity_guarded
from ._shared import append_trace, canonical_claim, require_view


@integrity_guarded
def remove_invariant_evidence(
    case: CanonicalCase,
    view: EvidenceView,
    *,
    invariant_id: str,
) -> EvidenceView:
    view = require_view(case, view)
    canonical_claim(view, invariant_id)  # validate target exists
    claims = tuple(item for item in view.claims if item.invariant_id != invariant_id)
    return append_trace(
        view,
        MutationTrace(kind="missing", target=invariant_id),
        claims=claims,
    )
