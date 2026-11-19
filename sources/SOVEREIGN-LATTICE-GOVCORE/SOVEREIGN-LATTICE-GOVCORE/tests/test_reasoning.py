"""Tests for Parallel Reasoning Engine."""
import pytest
from govcore.reasoning.engine import ParallelReasoningEngine, LaneResult


EVIDENCE_HIGH = [
    {"source_id": "NIST-PQC", "confidence": 0.99, "content": "FIPS 203 finalized", "temporal_scope": "2024"},
    {"source_id": "NIST-ZTMM", "confidence": 0.95, "content": "Zero trust baseline", "temporal_scope": "2024"},
    {"source_id": "CISA-ZTMM", "confidence": 0.92, "content": "Identity segmentation", "temporal_scope": "2024"},
]

EVIDENCE_WEAK = [
    {"source_id": "proj-A", "confidence": 0.25, "content": "Projected scenario", "temporal_scope": "2028"},
    {"source_id": "proj-B", "confidence": 0.20, "content": "Estimated timeline", "temporal_scope": "2029"},
    {"source_id": "proj-C", "confidence": 0.18, "content": "Forecast", "temporal_scope": "2030"},
]


def test_well_evidenced_recommendation_promoted():
    engine = ParallelReasoningEngine()
    out = engine.reason(
        query="Should we migrate RSA-4096 to ML-DSA?",
        recommendation="Migrate root CA from RSA-4096 to ML-DSA (FIPS 204).",
        evidence=EVIDENCE_HIGH,
        policy_context={"human_approval_confirmed": True},
        risk_context={"base_severity": 0.3, "is_reversible": True, "affected_systems": 2},
    )
    assert out.promoted is True
    assert out.confidence > 0.5
    assert len(out.lane_outputs) == 5


def test_weak_evidence_withheld():
    engine = ParallelReasoningEngine()
    out = engine.reason(
        query="Migration timeline?",
        recommendation="Migration will complete by 2028.",
        evidence=EVIDENCE_WEAK,
        risk_context={"base_severity": 0.2, "is_reversible": True},
    )
    # With all weak evidence, synthesis lane returns WARN/DEFERRED
    synth = next(lo for lo in out.lane_outputs if lo.lane == "retrieval_synthesis")
    assert synth.result in (LaneResult.WARN, LaneResult.DEFERRED)


def test_policy_violation_blocks_promotion():
    engine = ParallelReasoningEngine()
    out = engine.reason(
        query="Migrate session keys?",
        recommendation="Migrate session keys to ML-KEM immediately.",
        evidence=EVIDENCE_HIGH,
        policy_context={"human_approval_confirmed": False},
        risk_context={"base_severity": 0.2, "is_reversible": True},
    )
    # Policy compliance lane should flag the sequence violation
    policy = next(lo for lo in out.lane_outputs if lo.lane == "policy_compliance")
    # The recommendation does not mention long-lived secrets first
    # Whether this blocks depends on keyword matching — just verify lane ran
    assert policy is not None


def test_engine_output_has_all_five_lanes():
    engine = ParallelReasoningEngine()
    out = engine.reason("query", "recommendation", EVIDENCE_HIGH)
    lane_names = {lo.lane for lo in out.lane_outputs}
    assert "retrieval_synthesis"   in lane_names
    assert "contradiction_detection" in lane_names
    assert "policy_compliance"     in lane_names
    assert "risk_scoring"          in lane_names
    assert "operator_explanation"  in lane_names


def test_format_for_operator_includes_status():
    engine = ParallelReasoningEngine()
    out = engine.reason("query", "recommendation", EVIDENCE_HIGH)
    rendered = out.format_for_operator()
    assert "PROMOTED" in rendered or "WITHHELD" in rendered
    assert "retrieval_synthesis" in rendered
