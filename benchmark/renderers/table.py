"""Deterministic pipe-table renderer."""

from __future__ import annotations

from ..models import CanonicalCase
from ..presentation import EvidenceView, ensure_view
from ..transform_guard import integrity_guarded
from .base import artifact, scalar_text


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


@integrity_guarded
def render_table(case: CanonicalCase, view: EvidenceView | None = None):
    view = ensure_view(case, view)
    lines = [
        f"# {view.scenario_id} — {view.title}",
        f"Domain: {view.domain}",
        "",
        "| Claim | Invariant | Value | Epistemic | Source | Rank | Trusted | Provenance |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    for claim in view.claims:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape(claim.id),
                    _escape(claim.invariant_id),
                    _escape(scalar_text(claim.value)),
                    claim.epistemic_status.value,
                    _escape(claim.source_id),
                    str(claim.authority_rank),
                    str(claim.trusted).lower(),
                    _escape(",".join(claim.provenance)),
                ]
            )
            + " |"
        )
    if view.evidence:
        lines.extend(
            [
                "",
                "| Evidence | Source | Present | Supports transition |",
                "|---|---|---|---|",
            ]
        )
        for item in view.evidence:
            lines.append(
                f"| {_escape(item.id)} | {_escape(item.source_id)} | "
                f"{str(item.present).lower()} | {str(item.supports_transition).lower()} |"
            )
    if view.transitions:
        lines.extend(
            [
                "",
                "| Transition | From | To | Observed | Required evidence | Min rank |",
                "|---|---|---|---|---|---:|",
            ]
        )
        for item in view.transitions:
            lines.append(
                f"| {_escape(item.id)} | {_escape(item.from_invariant)} | "
                f"{_escape(item.to_invariant)} | {str(item.observed).lower()} | "
                f"{_escape(','.join(item.required_evidence))} | {item.minimum_authority_rank} |"
            )
    return artifact(view, "table", "\n".join(lines) + "\n")
