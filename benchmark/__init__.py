"""UNISON-StateBench v0.1 core package."""

from .loaders import load_case
from .oracle import derive_oracle
from .presentation import EvidenceView, RenderedArtifact, build_evidence_view
from .scoring import BenchmarkMetrics, TrialScore, aggregate_scores, score_trial
from .state_collapse import detect_state_collapses
from .trials import (
    EvaluationPolicy,
    GeneratedTrial,
    MutationKind,
    MutationPlan,
    Representation,
    TrialExpectation,
    derive_trial_expectation,
    generate_trial,
    generate_trial_matrix,
)

__all__ = [
    "load_case",
    "derive_oracle",
    "build_evidence_view",
    "EvidenceView",
    "RenderedArtifact",
    "detect_state_collapses",
    "Representation",
    "MutationKind",
    "MutationPlan",
    "EvaluationPolicy",
    "TrialExpectation",
    "GeneratedTrial",
    "derive_trial_expectation",
    "generate_trial",
    "generate_trial_matrix",
    "TrialScore",
    "BenchmarkMetrics",
    "score_trial",
    "aggregate_scores",
]
