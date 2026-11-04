"""Tests for Human Protection Plane."""
import pytest
from govcore.human.protection import HumanProtectionPlane, ConfidenceLabel


def test_high_confidence_label():
    p = HumanProtectionPlane()
    out = p.label_output("FIPS 203 finalized 2024.", 0.95, ["NIST docs"])
    assert out.confidence_label == ConfidenceLabel.HIGH
    assert out.escalation_flag is False


def test_uncertain_triggers_escalation():
    p = HumanProtectionPlane()
    out = p.label_output("Projected migration by 2028.", 0.18, ["Model projection"])
    assert out.confidence_label == ConfidenceLabel.UNCERTAIN
    assert out.escalation_flag is True


def test_render_contains_confidence():
    p = HumanProtectionPlane()
    out = p.label_output("FIPS 203 is finalized.", 0.95, ["NIST"])
    rendered = out.render()
    assert "HIGH CONFIDENCE" in rendered
    assert "FIPS 203" in rendered


def test_override_recorded():
    p = HumanProtectionPlane()
    rec = p.record_override("op_jones", "auto-isolate", "manual review", "False positive")
    assert rec["operator_id"] == "op_jones"
    assert p.status()["overrides_recorded"] == 1


def test_emergency_shutdown_deactivates():
    p = HumanProtectionPlane()
    assert p.is_active()
    p.emergency_shutdown("op_chen", "Active intrusion")
    assert not p.is_active()


def test_appeal_submission_and_status():
    p = HumanProtectionPlane()
    p.submit_appeal("user_123", "dec-ref-abc", "Evidence insufficient")
    assert p.status()["appeals_pending"] == 1


def test_rollback_readiness():
    p = HumanProtectionPlane()
    r = p.verify_rollback_readiness()
    assert r["shutdown_capability"] is True
    assert r["appeal_path"] is True
