"""
Governance Kernel — The Command and Policy Layer.

Holds mission policy, legal constraints, privacy rules, rights-impact
classifications, approval workflows, waiver logic, audit policy, and
escalation rules. Aligned to M-25-21, M-25-22, and NIST AI RMF.

Capability level: ANI, Reactive + Limited Memory, Symbolic / Rule-based.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

_log = logging.getLogger("govcore.governance")


class OperatingMode(Enum):
    ADVISORY    = "advisory"     # System recommends only
    ASSISTED    = "assisted"     # System prepares actions for approval
    BOUNDED     = "bounded"      # Reversible, pre-authorized tasks in narrow scopes
    HIGH_IMPACT = "high_impact"  # Always requires human approval + enhanced logging


@dataclass
class PolicyRule:
    rule_id:              str
    description:          str
    rights_impact:        bool  = False
    legal_constraint:     bool  = False
    requires_approval:    bool  = False
    escalation_threshold: float = 0.75
    waiver_eligible:      bool  = False
    audit_required:       bool  = True
    policy_label:         str   = ""


@dataclass
class ApprovalRequest:
    """Formal approval request for a proposed action."""
    request_id:      str
    proposed_action: str
    evidence:        str
    expected_effect: str
    risks:           str
    alternative:     str
    impact_severity: float
    operating_mode:  OperatingMode
    created_at:      str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    approved:        Optional[bool] = None
    approved_by:     Optional[str]  = None
    approved_at:     Optional[str]  = None

    def approve(self, approver: str) -> None:
        self.approved    = True
        self.approved_by = approver
        self.approved_at = datetime.now(timezone.utc).isoformat()

    def reject(self, approver: str) -> None:
        self.approved    = False
        self.approved_by = approver
        self.approved_at = datetime.now(timezone.utc).isoformat()


@dataclass
class GovernanceDecision:
    operating_mode:      OperatingMode
    permitted:           bool
    requires_approval:   bool
    escalation_required: bool
    applicable_rules:    List[str]
    human_review_level:  str
    audit_event:         Dict
    rationale:           str


class GovernanceKernel:
    """
    Command and policy layer for Sovereign Lattice GovCore.
    Evaluates proposed actions against policy rules and determines
    operating mode, approval requirements, and audit obligations.
    """

    HIGH_IMPACT_THRESHOLD = 0.75

    _POLICY_RULES: Dict[str, PolicyRule] = {
        "RULE-001": PolicyRule(
            rule_id="RULE-001",
            description="Critical infrastructure actions require human approval.",
            rights_impact=True, legal_constraint=True,
            requires_approval=True, escalation_threshold=0.6,
            policy_label="CRITICAL_INFRASTRUCTURE",
        ),
        "RULE-002": PolicyRule(
            rule_id="RULE-002",
            description="Actions affecting legal status, benefits, or liberty are HIGH_IMPACT.",
            rights_impact=True, legal_constraint=True,
            requires_approval=True, escalation_threshold=0.5,
            policy_label="RIGHTS_IMPACT",
        ),
        "RULE-003": PolicyRule(
            rule_id="RULE-003",
            description="Scenario outputs cannot be promoted to established fact.",
            rights_impact=False, requires_approval=False,
            audit_required=True, policy_label="TEMPORAL_SEPARATION",
        ),
        "RULE-004": PolicyRule(
            rule_id="RULE-004",
            description="Privacy-impacting actions require notice controls.",
            rights_impact=True, requires_approval=True,
            escalation_threshold=0.65, policy_label="PRIVACY",
        ),
        "RULE-005": PolicyRule(
            rule_id="RULE-005",
            description="Irreversible actions require explicit human authorization.",
            rights_impact=True, requires_approval=True,
            escalation_threshold=0.0, policy_label="IRREVERSIBILITY",
        ),
        "RULE-006": PolicyRule(
            rule_id="RULE-006",
            description="PQC migration requires sequencing compliance (long-lived secrets first).",
            rights_impact=False, requires_approval=True,
            audit_required=True, policy_label="PQC_MIGRATION",
        ),
        "RULE-007": PolicyRule(
            rule_id="RULE-007",
            description="Protected group data requires enhanced audit logging.",
            rights_impact=True, requires_approval=True,
            escalation_threshold=0.55, audit_required=True,
            policy_label="PROTECTED_GROUPS",
        ),
    }

    def __init__(self, high_impact_threshold: float = 0.75):
        self.threshold    = high_impact_threshold
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._audit_log:  List[Dict] = []
        _log.info("GovernanceKernel online.")

    def evaluate_operating_mode(self, context: Dict) -> GovernanceDecision:
        """
        Evaluate what operating mode and approval level apply given context.

        Context keys:
          impact_severity (float 0-1)
          action_type (str): e.g. "network_isolation", "recommendation"
          is_reversible (bool)
          policy_labels (list[str])
          affects_critical_infrastructure (bool)
          affects_protected_groups (bool)
        """
        severity   = float(context.get("impact_severity", 0.0))
        reversible = bool(context.get("is_reversible", True))
        action_type = context.get("action_type", "recommendation")
        labels      = set(context.get("policy_labels", []))

        applicable = []
        for rule_id, rule in self._POLICY_RULES.items():
            if rule.policy_label in labels:
                applicable.append(rule_id)
            if not reversible and rule.policy_label == "IRREVERSIBILITY":
                applicable.append(rule_id)
            if context.get("affects_critical_infrastructure") and rule.policy_label == "CRITICAL_INFRASTRUCTURE":
                applicable.append(rule_id)
            if context.get("affects_protected_groups") and rule.policy_label == "PROTECTED_GROUPS":
                applicable.append(rule_id)

        requires_approval = (
            any(self._POLICY_RULES[r].requires_approval for r in applicable)
            or severity >= self.threshold
        )

        if not reversible or severity >= self.threshold or context.get("affects_critical_infrastructure"):
            mode = OperatingMode.HIGH_IMPACT
        elif requires_approval:
            mode = OperatingMode.ASSISTED
        elif action_type in ("recommendation", "summary", "analysis"):
            mode = OperatingMode.ADVISORY
        else:
            mode = OperatingMode.BOUNDED

        escalation = (
            mode == OperatingMode.HIGH_IMPACT
            or any(severity >= self._POLICY_RULES[r].escalation_threshold for r in applicable)
        )

        human_review = "none"
        if mode == OperatingMode.HIGH_IMPACT:
            human_review = "enhanced"
        elif requires_approval:
            human_review = "standard"

        audit_event = {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "mode":          mode.value,
            "severity":      severity,
            "action_type":   action_type,
            "rules_applied": list(set(applicable)),
            "escalated":     escalation,
        }
        self._audit_log.append(audit_event)

        return GovernanceDecision(
            operating_mode      = mode,
            permitted           = True,
            requires_approval   = requires_approval,
            escalation_required = escalation,
            applicable_rules    = list(set(applicable)),
            human_review_level  = human_review,
            audit_event         = audit_event,
            rationale           = f"Severity={severity:.2f}, mode={mode.value}, rules={list(set(applicable))}",
        )

    def create_approval_request(
        self,
        proposed_action: str,
        evidence:        str,
        expected_effect: str,
        risks:           str,
        alternative:     str,
        impact_severity: float,
        operating_mode:  OperatingMode,
    ) -> ApprovalRequest:
        req_id = hashlib.sha256(
            f"{proposed_action}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        request = ApprovalRequest(
            request_id=req_id, proposed_action=proposed_action,
            evidence=evidence, expected_effect=expected_effect,
            risks=risks, alternative=alternative,
            impact_severity=impact_severity, operating_mode=operating_mode,
        )
        self._approvals[req_id] = request
        _log.info(f"Approval request [{req_id}]: {proposed_action[:60]}")
        return request

    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._approvals.get(request_id)

    def pending_approvals(self) -> List[ApprovalRequest]:
        return [r for r in self._approvals.values() if r.approved is None]

    def audit_summary(self) -> Dict:
        return {
            "total_evaluations": len(self._audit_log),
            "high_impact_count": sum(1 for e in self._audit_log if e["mode"] == "high_impact"),
            "escalation_count":  sum(1 for e in self._audit_log if e["escalated"]),
            "pending_approvals": len(self.pending_approvals()),
        }
