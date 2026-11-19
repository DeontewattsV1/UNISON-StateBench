"""Tests for Agent Plane."""
import pytest
from govcore.agents.bounded_agents import WatchfloorAgent, PQCMigrationAgent, AuditAgent, AgentPlane


def test_watchfloor_unauthorized_returns_empty():
    agent = WatchfloorAgent()
    recs = agent.triage([{"severity": 0.9, "description": "anomaly"}])
    assert recs == []


def test_watchfloor_authorized_produces_recs():
    agent = WatchfloorAgent()
    agent.authenticate("test-token")
    events = [
        {"severity": 0.85, "description": "Lateral movement", "source": "SIEM"},
        {"severity": 0.3,  "description": "Normal traffic",   "source": "fw"},
    ]
    recs = agent.triage(events)
    assert len(recs) == 1
    assert recs[0].confidence >= 0.7


def test_pqc_recommends_rsa_migration():
    agent = PQCMigrationAgent()
    agent.authenticate("test-token")
    inv = [
        {"name": "root_ca", "algorithm": "RSA-4096", "use": "signing", "sensitivity": "critical", "component_class": "root_ca_certificates"},
        {"name": "hmac",    "algorithm": "HMAC-SHA256", "use": "auth", "sensitivity": "standard"},
    ]
    recs = agent.assess_readiness(inv)
    assert len(recs) == 1
    assert "RSA" in recs[0].evidence
    assert recs[0].requires_human_approval is True


def test_audit_ledger_integrity():
    agent = AuditAgent()
    agent.log_event("ADJUDICATION", "Watchfloor", "Anomaly triaged")
    agent.log_event("RECOMMENDATION", "PQC", "Migration plan generated")
    check = agent.verify_completeness()
    assert check["valid"] is True
    assert check["entries"] == 2


def test_agent_plane_authorize_all():
    plane = AgentPlane()
    plane.authorize_all("session-abc")
    status = plane.status()
    assert status["cyber_defense"]["authorized"] is True
    assert status["pqc_migration"]["authorized"] is True
