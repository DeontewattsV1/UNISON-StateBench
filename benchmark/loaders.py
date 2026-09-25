"""Fixture loading helpers."""

from __future__ import annotations

from pathlib import Path

from .models import CanonicalCase


def load_case(path: str | Path) -> CanonicalCase:
    return CanonicalCase.model_validate_json(Path(path).read_text(encoding="utf-8"))
