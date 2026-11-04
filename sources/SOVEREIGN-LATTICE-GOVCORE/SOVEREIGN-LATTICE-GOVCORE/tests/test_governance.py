"""Tests for Governance Kernel."""
import pytest
from govcore.governance.kernel import GovernanceKernel, OperatingMode


def test_advisory_mode_for_low_severity():
    k = GovernanceKernel()
    d = k.evaluate_operating_mode({"impact_severity": 0.1, "action_type": "recommendation", "is_reversible": True})
    assert d.operating_mode == OperatingMode.ADVISORY


def test_high_impact_for_high_severity():
    k = GovernanceKernel()
    d = k.evaluate_operating_mode({"impact_severity": 0.9, "action_type": "network_isolation", "is_reversible": False})
    assert d.operating_mode == OperatingMode.HIGH_IMPACT
    assert d.requires_approval is True
    assert d.human_review_level == "enhanced"


def test_critical_infra_always_high_impact():
    k = GovernanceKernel()
    d = k.evaluate_operating_mode({"impact_severity": 0.3, "action_type": "config_change", "is_reversible": True, "affects_critical_infrastructure": True})
    assert d.operating_mode == OperatingMode.HIGH_IMPACT


def test_approval_request_pending():
    k = GovernanceKernel()
    req = k.create_approval_request("Isolate subnet", "Anomaly 0.92", "Contain LM", "Disruption", "Alert-only", 0.85, OperatingMode.HIGH_IMPACT)
    assert req.approved is None
    assert len(k.pending_approvals()) == 1


def test_approve_clears_pending():
    k = GovernanceKernel()
    req = k.create_approval_request("action", "ev", "eff", "risk", "alt", 0.9, OperatingMode.HIGH_IMPACT)
    req.approve("operator_jones")
    assert req.approved is True
    assert len(k.pending_approvals()) == 0


def test_audit_summary():
    k = GovernanceKernel()
    k.evaluate_operating_mode({"impact_severity": 0.1})
    k.evaluate_operating_mode({"impact_severity": 0.9, "is_reversible": False})
    s = k.audit_summary()
    assert s["total_evaluations"] == 2
    assert s["high_impact_count"] >= 1


def test_protected_groups_rule():
    k = GovernanceKernel()
    d = k.evaluate_operating_mode({"impact_severity": 0.2, "affects_protected_groups": True})
    assert d.requires_approval is True
    assert "RULE-007" in d.applicable_rules
