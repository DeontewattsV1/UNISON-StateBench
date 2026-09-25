"""Guarded deterministic presentation mutations."""

from .adversarial import adversarial_flip
from .authority_conflict import inject_authority_conflict
from .contradiction import inject_contradiction
from .missing import remove_invariant_evidence
from .paraphrase import paraphrase_view
from .reorder import reorder_view

__all__ = [
    "reorder_view",
    "paraphrase_view",
    "inject_contradiction",
    "remove_invariant_evidence",
    "inject_authority_conflict",
    "adversarial_flip",
]
