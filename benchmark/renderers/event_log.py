"""Deterministic event-log renderer.

Sequence numbers are representation identifiers, not claims of real chronology.
"""

from __future__ import annotations

from ..models import CanonicalCase
from ..presentation import EvidenceView, ensure_view
from ..transform_guard import integrity_guarded
from .base import artifact, scalar_text


def _clean(value: str) -> str:
    return value.replace("\n", " ").replace(" ", "_")


@integrity_guarded
def render_event_log(case: CanonicalCase, view: EvidenceView | None = None):
    view = ensure_view(case, view)
    lines = [
        f"0000 SCENARIO id={view.scenario_id} domain={_clean(view.domain)} title={_clean(view.title)}"
    ]
    seq = 10
    for source in view.sources:
        lines.append(
            f"{seq:04d} SOURCE id={source.id} rank={source.authority_rank} "
            f"trusted={str(source.trusted).lower()} kind={_clean(source.kind)}"
        )
        seq += 10
    seq = 1000
    for claim in view.claims:
        provenance = ",".join(claim.provenance) or "none"
        lines.append(
            f"{seq:04d} CLAIM id={claim.id} invariant={claim.invariant_id} "
            f"value={_clean(scalar_text(claim.value))} status={claim.epistemic_status.value} "
            f"source={claim.source_id} rank={claim.authority_rank} "
            f"trusted={str(claim.trusted).lower()} provenance={_clean(provenance)} "
            f"injected={str(claim.injected).lower()}"
        )
        seq += 10
    seq = 2000
    for item in view.evidence:
        lines.append(
            f"{seq:04d} EVIDENCE id={item.id} source={item.source_id} "
            f"present={str(item.present).lower()} "
            f"supports_transition={str(item.supports_transition).lower()}"
        )
        seq += 10
    seq = 3000
    for item in view.transitions:
        required = ",".join(item.required_evidence) or "none"
        lines.append(
            f"{seq:04d} TRANSITION id={item.id} from={item.from_invariant} "
            f"to={item.to_invariant} observed={str(item.observed).lower()} "
            f"required={_clean(required)} min_rank={item.minimum_authority_rank}"
        )
        seq += 10
    return artifact(view, "event_log", "\n".join(lines) + "\n")
