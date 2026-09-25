"""Deterministic surface-form paraphrase mutation."""

from __future__ import annotations

from ..models import CanonicalCase
from ..presentation import EvidenceView, MutationTrace, PresentedClaim
from ..transform_guard import integrity_guarded
from ._shared import append_trace, require_view


def _paraphrase_claim(claim: PresentedClaim) -> PresentedClaim:
    semantic = (
        f"Reported state for {claim.invariant_id}: value={claim.value!r}; "
        f"epistemic_status={claim.epistemic_status.value}; source={claim.source_id}."
    )
    return claim.model_copy(update={"description": semantic})


@integrity_guarded
def paraphrase_view(case: CanonicalCase, view: EvidenceView) -> EvidenceView:
    view = require_view(case, view)
    claims = tuple(_paraphrase_claim(item) for item in view.claims)
    return append_trace(
        view,
        MutationTrace(
            kind="paraphrase",
            details=("controlled_template=v1", "semantic_fields_unchanged=true"),
        ),
        title=f"Evidence state for {view.scenario_id}",
        claims=claims,
    )
