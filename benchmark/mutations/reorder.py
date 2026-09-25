"""Deterministic order mutation."""

from __future__ import annotations

from ..models import CanonicalCase
from ..presentation import EvidenceView, MutationTrace
from ..transform_guard import integrity_guarded
from ._shared import append_trace, require_view


@integrity_guarded
def reorder_view(
    case: CanonicalCase,
    view: EvidenceView,
    *,
    mode: str = "reverse",
) -> EvidenceView:
    view = require_view(case, view)
    if mode == "reverse":
        reorder = lambda items: tuple(reversed(items))
    elif mode == "rotate_left":
        reorder = lambda items: items[1:] + items[:1] if items else items
    else:
        raise ValueError("mode must be 'reverse' or 'rotate_left'")
    return append_trace(
        view,
        MutationTrace(kind="reorder", details=(f"mode={mode}",)),
        claims=reorder(view.claims),
        sources=reorder(view.sources),
        evidence=reorder(view.evidence),
        transitions=reorder(view.transitions),
    )
