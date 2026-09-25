"""Shared deterministic renderer helpers."""

from __future__ import annotations

import json

from ..models import JsonScalar
from ..presentation import EvidenceView, RenderedArtifact


def scalar_text(value: JsonScalar) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return str(value)


def json_scalar(value: JsonScalar) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def artifact(view: EvidenceView, fmt: str, content: str) -> RenderedArtifact:
    return RenderedArtifact(
        scenario_id=view.scenario_id,
        format=fmt,  # type: ignore[arg-type]
        content=content,
        origin_case_digest=view.origin_case_digest,
        origin_oracle_digest=view.origin_oracle_digest,
        mutation_trace=view.mutation_trace,
    )
