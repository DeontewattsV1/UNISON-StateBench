"""Integrity guard for renderers and controlled presentation mutations."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar

from .integrity import assert_unchanged, snapshot
from .models import CanonicalCase

P = ParamSpec("P")
R = TypeVar("R")


def run_guarded_transform(
    case: CanonicalCase,
    transform: Callable[Concatenate[CanonicalCase, P], R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Execute a transform and prove canonical state/oracle are unchanged afterward.

    The post-check executes even when the transform raises, so an implementation
    cannot silently corrupt canonical truth and escape detection behind an error.
    """
    before = snapshot(case)
    try:
        result = transform(case, *args, **kwargs)
    except BaseException as exc:
        try:
            assert_unchanged(before, case)
        except AssertionError as integrity_exc:
            raise integrity_exc from exc
        raise
    assert_unchanged(before, case)
    return result


def integrity_guarded(
    transform: Callable[Concatenate[CanonicalCase, P], R],
) -> Callable[Concatenate[CanonicalCase, P], R]:
    """Decorator making integrity verification mandatory for a public transform."""

    @wraps(transform)
    def wrapper(case: CanonicalCase, *args: P.args, **kwargs: P.kwargs) -> R:
        return run_guarded_transform(case, transform, *args, **kwargs)

    return wrapper
