"""Apply a minimal silent corruption to a presented claim.

Unlike contradiction/authority-conflict mutations, this replaces a presentation
claim instead of adding a second claim. Canonical truth and oracle remain fixed.
"""

from __future__ import annotations

from ..models import CanonicalCase, JsonScalar
from ..presentation import EvidenceView, MutationTrace
from ..transform_guard import integrity_guarded
from ._shared import append_trace, canonical_claim, flipped_value, require_view


@integrity_guarded
def adversarial_flip(
    case: CanonicalCase,
    view: EvidenceView,
    *,
    invariant_id: str,
    replacement_value: JsonScalar | None = None,
) -> EvidenceView:
    view = require_view(case, view)
    index, canonical = canonical_claim(view, invariant_id)
    value = flipped_value(canonical.value) if replacement_value is None else replacement_value
    if value == canonical.value:
        raise ValueError("Adversarial replacement must change the presented value")
    corrupted = canonical.model_copy(
        update={
            "value": value,
            "description": "Adversarially modified presentation value.",
            "injected": True,
            "id": f"MUT:ADVERSARIAL:{canonical.id}",
        }
    )
    claims = list(view.claims)
    claims[index] = corrupted
    return append_trace(
        view,
        MutationTrace(
            kind="adversarial",
            target=invariant_id,
            details=(f"replacement_value={value!r}", "canonical_oracle_unchanged=true"),
        ),
        claims=tuple(claims),
    )
