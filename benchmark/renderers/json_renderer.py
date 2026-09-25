"""Deterministic JSON renderer."""

from __future__ import annotations

import json

from ..models import CanonicalCase
from ..presentation import EvidenceView, ensure_view
from ..transform_guard import integrity_guarded
from .base import artifact


def _payload(view: EvidenceView) -> dict:
    return {
        "scenario_id": view.scenario_id,
        "domain": view.domain,
        "title": view.title,
        "claims": [claim.model_dump(mode="json", exclude_none=False) for claim in view.claims],
        "sources": [source.model_dump(mode="json", exclude_none=False) for source in view.sources],
        "evidence": [item.model_dump(mode="json", exclude_none=False) for item in view.evidence],
        "transitions": [item.model_dump(mode="json", exclude_none=False) for item in view.transitions],
        "notes": list(view.notes),
        "mutation_trace": [item.model_dump(mode="json") for item in view.mutation_trace],
    }


@integrity_guarded
def render_json(case: CanonicalCase, view: EvidenceView | None = None):
    view = ensure_view(case, view)
    content = json.dumps(
        _payload(view),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
    ) + "\n"
    return artifact(view, "json", content)
