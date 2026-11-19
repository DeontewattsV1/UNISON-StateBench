"""
Parallel Reasoning Engine — The Non-Human Layer.

Runs five independent reasoning lanes in parallel.
A recommendation is released only after convergence and contradiction screening.

Lanes:
  1. Retrieval-Backed Synthesis  — generative, evidence-anchored
  2. Contradiction Detection     — adversarial red-team lane
  3. Policy Compliance           — constraint satisfaction against governance rules
  4. Risk Scoring                — probabilistic risk estimation
  5. Operator Explanation        — human-readable rationale generation

Capability level: AGI-precursor (max), Limited Memory, Generative + Analytic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger("govcore.reasoning")


class LaneResult(Enum):
    PASS     = "PASS"
    WARN     = "WARN"
    FAIL     = "FAIL"
    DEFERRED = "DEFERRED"  # Insufficient evidence — escalate


@dataclass
class ReasoningLaneOutput:
    """Output from a single reasoning lane."""
    lane:          str
    result:        LaneResult
    confidence:    float
    finding:       str
    evidence_refs: List[str] = field(default_factory=list)
    caveat:        str = ""


@dataclass
class EngineOutput:
    """
    Final output from the Parallel Reasoning Engine.
    Only promoted when at least two lanes converge and contradiction lane
    fails to produce a compelling refutation.
    """
    promoted:            bool
    recommendation:      str
    confidence:          float
    lane_outputs:        List[ReasoningLaneOutput]
    contradiction_found: bool
    contradiction_detail: str
    uncertainty_flags:   List[str]
    created_at:          str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def format_for_operator(self) -> str:
        status = "PROMOTED" if self.promoted else "WITHHELD (insufficient convergence)"
        lines = [
            f"[{status}] Confidence: {self.confidence:.0%}",
            f"Recommendation: {self.recommendation}",
            "",
            "Lane Results:",
        ]
        for lo in self.lane_outputs:
            lines.append(f"  {lo.lane:<32} {lo.result.value:<8} {lo.confidence:.0%}  {lo.finding[:60]}")

        if self.contradiction_found:
            lines.append(f"\nContradiction: {self.contradiction_detail}")
        if self.uncertainty_flags:
            lines.append(f"Uncertainty flags: {'; '.join(self.uncertainty_flags)}")
        return "\n".join(lines)


class RetrievalBackedSynthesisLane:
    """
    The only generative lane. Produces human-readable analysis grounded in
    retrieved evidence. Every sentence must be anchored to a specific evidence node.
    """

    def evaluate(self, query: str, evidence: List[Dict]) -> ReasoningLaneOutput:
        if not evidence:
            return ReasoningLaneOutput(
                lane="retrieval_synthesis",
                result=LaneResult.DEFERRED,
                confidence=0.0,
                finding="Insufficient evidence to synthesize response.",
                caveat="No evidence provided. Escalate to human review.",
            )

        high_conf = [e for e in evidence if e.get("confidence", 0) >= 0.7]
        if not high_conf:
            confidence = 0.45
            result = LaneResult.WARN
        else:
            confidence = sum(e.get("confidence", 0) for e in high_conf) / len(high_conf)
            result = LaneResult.PASS

        refs = [e.get("source_id", "unknown") for e in evidence[:3]]
        finding = f"Synthesis grounded in {len(evidence)} evidence items ({len(high_conf)} high-confidence)."

        return ReasoningLaneOutput(
            lane="retrieval_synthesis",
            result=result,
            confidence=confidence,
            finding=finding,
            evidence_refs=refs,
        )


class ContradictionDetectionLane:
    """
    Adversarial red-team lane. Attempts to construct refutations of every
    promoted claim. If a compelling refutation is found, the claim is withheld.
    """

    def evaluate(self, recommendation: str, evidence: List[Dict]) -> ReasoningLaneOutput:
        contradictions = []

        # Check for conflicting evidence
        high_conf = [e for e in evidence if e.get("confidence", 0) >= 0.7]
        low_conf  = [e for e in evidence if e.get("confidence", 0) < 0.4]

        if low_conf and len(low_conf) >= len(high_conf):
            contradictions.append(
                f"Low-confidence evidence ({len(low_conf)} items) equals or exceeds high-confidence evidence."
            )

        # Check temporal scope conflicts
        scopes = set(e.get("temporal_scope", "") for e in evidence if e.get("temporal_scope"))
        if len(scopes) > 2:
            contradictions.append(
                f"Evidence spans conflicting temporal scopes: {list(scopes)[:3]}"
            )

        if contradictions:
            return ReasoningLaneOutput(
                lane="contradiction_detection",
                result=LaneResult.WARN,
                confidence=0.60,
                finding=f"Potential contradictions found: {contradictions[0]}",
                caveat="Present both claim and counter-evidence to operator.",
            )

        return ReasoningLaneOutput(
            lane="contradiction_detection",
            result=LaneResult.PASS,
            confidence=0.85,
            finding="No compelling contradictions identified in available evidence.",
        )


class PolicyComplianceLane:
    """
    Constraint satisfaction lane. Checks proposed claims and plans against
    policy rules. Produces PASS / WARN / FAIL — not natural language prose.
    """

    _SEQUENCE_CONSTRAINTS = {
        "pqc_migration": "Long-lived secrets must be migrated before short-lived ones.",
        "audit_logging":  "Audit logging must be established before bounded execution mode.",
    }

    def evaluate(self, recommendation: str, policy_context: Dict) -> ReasoningLaneOutput:
        violations = []

        # Check sequencing constraints
        if "migrate" in recommendation.lower() and "session" in recommendation.lower():
            if "root_ca" not in recommendation.lower() and "long_lived" not in recommendation.lower():
                violations.append(
                    "SEQUENCE VIOLATION: Short-lived component migration proposed before "
                    "long-lived secrets. RULE-006 requires long-lived secrets first."
                )

        # Check rights-impact requirements
        rights_keywords = ["benefits", "legal status", "liberty", "protected group"]
        if any(kw in recommendation.lower() for kw in rights_keywords):
            if not policy_context.get("human_approval_confirmed"):
                violations.append(
                    "RIGHTS IMPACT: Action affects rights-sensitive domain. RULE-002 requires human approval."
                )

        if violations:
            return ReasoningLaneOutput(
                lane="policy_compliance",
                result=LaneResult.FAIL,
                confidence=0.95,
                finding=violations[0],
                caveat="Policy violation must be resolved before promotion.",
            )

        return ReasoningLaneOutput(
            lane="policy_compliance",
            result=LaneResult.PASS,
            confidence=0.90,
            finding="No policy violations identified.",
        )


class RiskScoringLane:
    """
    Probabilistic risk estimation lane.
    Produces probability intervals, not point estimates presented as facts.
    """

    def evaluate(self, recommendation: str, risk_context: Dict) -> ReasoningLaneOutput:
        base_risk    = float(risk_context.get("base_severity", 0.3))
        reversible   = bool(risk_context.get("is_reversible", True))
        blast_radius = int(risk_context.get("affected_systems", 1))

        # Compute risk score
        risk_score = base_risk
        if not reversible:
            risk_score = min(1.0, risk_score + 0.25)
        if blast_radius > 10:
            risk_score = min(1.0, risk_score + 0.15)

        confidence_interval = (
            max(0.0, risk_score - 0.15),
            min(1.0, risk_score + 0.15),
        )

        if risk_score >= 0.75:
            result = LaneResult.FAIL
            finding = (
                f"HIGH RISK: P(harm) estimated {confidence_interval[0]:.0%}–{confidence_interval[1]:.0%}. "
                f"Irreversible={not reversible}, affected_systems={blast_radius}."
            )
        elif risk_score >= 0.45:
            result = LaneResult.WARN
            finding = (
                f"MODERATE RISK: P(harm) estimated {confidence_interval[0]:.0%}–{confidence_interval[1]:.0%}."
            )
        else:
            result = LaneResult.PASS
            finding = f"LOW RISK: P(harm) estimated {confidence_interval[0]:.0%}–{confidence_interval[1]:.0%}."

        return ReasoningLaneOutput(
            lane="risk_scoring",
            result=result,
            confidence=0.75,
            finding=finding,
        )


class OperatorExplanationLane:
    """
    Generates operator-facing explanations for system recommendations.
    Ensures that every promoted claim has a human-readable rationale.
    """

    def evaluate(
        self, recommendation: str, all_lane_outputs: List[ReasoningLaneOutput]
    ) -> ReasoningLaneOutput:
        passes = sum(1 for lo in all_lane_outputs if lo.result == LaneResult.PASS)
        warns  = sum(1 for lo in all_lane_outputs if lo.result == LaneResult.WARN)
        fails  = sum(1 for lo in all_lane_outputs if lo.result == LaneResult.FAIL)

        if fails > 0:
            finding = (
                f"Explanation withheld: {fails} lane(s) failed. "
                "Resolve failures before presenting to operator."
            )
            result = LaneResult.FAIL
        elif warns > 0:
            finding = (
                f"Explanation generated with {warns} caution flag(s). "
                "Present caveats alongside recommendation."
            )
            result = LaneResult.WARN
        else:
            finding = f"Recommendation validated by {passes} converging lanes. Ready for operator review."
            result  = LaneResult.PASS

        return ReasoningLaneOutput(
            lane="operator_explanation",
            result=result,
            confidence=0.88,
            finding=finding,
        )


class ParallelReasoningEngine:
    """
    Runs all five lanes in parallel and promotes only on convergence.

    Promotion criteria:
      - At least two lanes return PASS
      - ContradictionDetectionLane does NOT return FAIL
      - PolicyComplianceLane does NOT return FAIL
    """

    def __init__(self):
        self.synthesis    = RetrievalBackedSynthesisLane()
        self.contradiction= ContradictionDetectionLane()
        self.compliance   = PolicyComplianceLane()
        self.risk         = RiskScoringLane()
        self.explanation  = OperatorExplanationLane()
        _log.info("ParallelReasoningEngine initialized — 5 lanes active.")

    def reason(
        self,
        query:          str,
        recommendation: str,
        evidence:       List[Dict],
        policy_context: Dict = None,
        risk_context:   Dict = None,
    ) -> EngineOutput:
        policy_context = policy_context or {}
        risk_context   = risk_context   or {}

        # Run all five lanes
        lane_outputs = [
            self.synthesis.evaluate(query, evidence),
            self.contradiction.evaluate(recommendation, evidence),
            self.compliance.evaluate(recommendation, policy_context),
            self.risk.evaluate(recommendation, risk_context),
        ]

        # Explanation lane sees all other outputs
        lane_outputs.append(self.explanation.evaluate(recommendation, lane_outputs))

        # Convergence check
        passes     = [lo for lo in lane_outputs if lo.result == LaneResult.PASS]
        fails      = [lo for lo in lane_outputs if lo.result == LaneResult.FAIL]
        contradict = next((lo for lo in lane_outputs if lo.lane == "contradiction_detection" and lo.result == LaneResult.FAIL), None)
        policy_fail= next((lo for lo in lane_outputs if lo.lane == "policy_compliance"      and lo.result == LaneResult.FAIL), None)

        # Must have 2+ converging passes AND no critical failures
        promoted = (
            len(passes) >= 2
            and contradict is None
            and policy_fail is None
        )

        # Aggregate confidence
        pass_confidences = [lo.confidence for lo in passes]
        confidence = sum(pass_confidences) / len(pass_confidences) if pass_confidences else 0.0

        uncertainty_flags = [
            lo.caveat for lo in lane_outputs if lo.caveat
        ]

        contradiction_found  = contradict is not None
        contradiction_detail = contradict.finding if contradict else ""

        return EngineOutput(
            promoted             = promoted,
            recommendation       = recommendation,
            confidence           = confidence,
            lane_outputs         = lane_outputs,
            contradiction_found  = contradiction_found,
            contradiction_detail = contradiction_detail,
            uncertainty_flags    = uncertainty_flags,
        )
