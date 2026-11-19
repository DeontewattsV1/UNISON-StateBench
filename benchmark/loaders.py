"""Strict fixture loading helpers for canonical benchmark state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CanonicalCase


class CanonicalJsonError(ValueError):
    """Raised when a canonical fixture is not strict, unambiguous JSON."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalJsonError(f"Duplicate JSON key is not allowed: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str):
    raise CanonicalJsonError(
        f"Non-finite JSON numeric constant is not allowed in canonical state: {value}"
    )


def load_case(path: str | Path) -> CanonicalCase:
    """Load one canonical case with duplicate-key and non-finite-number rejection."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise CanonicalJsonError(f"Invalid canonical JSON: {exc.msg}") from exc
    return CanonicalCase.model_validate(payload)
