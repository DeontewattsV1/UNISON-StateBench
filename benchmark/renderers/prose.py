"""Deterministic prose renderer."""

from __future__ import annotations

from ..models import CanonicalCase
from ..presentation import EvidenceView, ensure_view
from ..transform_guard import integrity_guarded
from .base import artifact, scalar_text


@integrity_guarded
def render_prose(case: CanonicalCase, view: EvidenceView | None = None):
    view = ensure_view(case, view)
    lines = [
        f"Scenario {view.scenario_id}: {view.title}",
        f"Domain: {view.domain}.",
        "Claims:",
    ]
    for claim in view.claims:
        description = f" {claim.description}" if claim.description else ""
        provenance = ", ".join(claim.provenance) if claim.provenance else "none"
        lines.append(
            "- "
            f"{claim.invariant_id} is {scalar_text(claim.value)} "
            f"with epistemic status {claim.epistemic_status.value}; "
            f"source={claim.source_id}, authority_rank={claim.authority_rank}, "
            f"trusted={str(claim.trusted).lower()}, provenance={provenance}."
            f"{description}"
        )
    if view.evidence:
        lines.append("Evidence records:")
        for item in view.evidence:
            lines.append(
                "- "
                f"{item.id}: source={item.source_id}, present={str(item.present).lower()}, "
                f"supports_transition={str(item.supports_transition).lower()}."
            )
    if view.transitions:
        lines.append("Transition requirements:")
        for transition in view.transitions:
            required = ", ".join(transition.required_evidence) or "none"
            lines.append(
                "- "
                f"{transition.id}: {transition.from_invariant} -> {transition.to_invariant}; "
                f"observed={str(transition.observed).lower()}; required_evidence={required}; "
                f"minimum_authority_rank={transition.minimum_authority_rank}."
            )
    return artifact(view, "prose", "\n".join(lines) + "\n")
