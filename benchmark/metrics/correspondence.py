"""Representation Correspondence Rate (RCR)."""

from __future__ import annotations

from itertools import combinations


def pairwise_correspondence(signatures: tuple[str, ...]) -> tuple[int, int]:
    """Return equal-pair count and tested-pair count for one equivalence group."""
    pairs = tuple(combinations(signatures, 2))
    return sum(left == right for left, right in pairs), len(pairs)
