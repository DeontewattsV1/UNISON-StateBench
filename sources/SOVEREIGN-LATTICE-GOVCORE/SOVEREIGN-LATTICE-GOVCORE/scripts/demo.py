"""
Sovereign Lattice GovCore — Demo
Illustrates Governance Kernel + Agent Plane + Human Protection Plane.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govcore.governance.kernel import GovernanceKernel, OperatingMode
from govcore.agents.bounded_agents import AgentPlane
from govcore.human.protection import HumanProtectionPlane


def run():
    print("\n══ SOVEREIGN LATTICE GOVCORE — Demo ══\n")

    kernel = GovernanceKernel()
    plane  = AgentPlane()
    human  = HumanProtectionPlane()
    plane.authorize_all("demo-session-2026")

    # ── Scenario 1: Advisory recommendation ─────────────────────────────
    print("── Scenario 1: Advisory Recommendation ──")
    decision = kernel.evaluate_operating_mode({
        "impact_severity": 0.2,
        "action_type":     "recommendation",
        "is_reversible":   True,
    })
    print(f"Mode: {decision.operating_mode.value}  Approval required: {decision.requires_approval}")
    output = human.label_output(
        "FIPS 203/204/205 are finalized NIST PQC standards (Aug 2024).",
        confidence=0.99,
        sources=["NIST PQC documentation"],
    )
    print(output.render())
    print()

    # ── Scenario 2: High-impact action ─────────────────────────────────
    print("── Scenario 2: High-Impact Action ──")
    decision2 = kernel.evaluate_operating_mode({
        "impact_severity":              0.88,
        "action_type":                  "network_isolation",
        "is_reversible":                False,
        "affects_critical_infrastructure": True,
    })
    print(f"Mode: {decision2.operating_mode.value}  Human review: {decision2.human_review_level}")
    req = kernel.create_approval_request(
        proposed_action="Isolate subnet 10.0.1.0/24",
        evidence="Anomaly score 0.92 detected via Watchfloor Agent",
        expected_effect="Contain suspected lateral movement.",
        risks="Service disruption for 12 endpoints on subnet.",
        alternative="Alert-only mode pending manual investigation.",
        impact_severity=0.88,
        operating_mode=OperatingMode.HIGH_IMPACT,
    )
    print(f"Approval request [{req.request_id}] created — awaiting human decision.")
    print()

    # ── Scenario 3: PQC Migration planning ──────────────────────────────
    print("── Scenario 3: PQC Migration Recommendations ──")
    inventory = [
        {"name": "root_ca",         "algorithm": "RSA-4096",  "use": "signing",  "sensitivity": "critical",  "component_class": "root_ca_certificates"},
        {"name": "inter_svc_tls",   "algorithm": "ECDH-P256", "use": "key_exchange", "sensitivity": "high",  "component_class": "inter_service_trust"},
        {"name": "session_hmac",    "algorithm": "HMAC-SHA256","use": "auth",     "sensitivity": "standard",  "component_class": "session_keys"},
    ]
    recs = plane.pqc.assess_readiness(inventory)
    for r in recs:
        print(r.format_for_operator())
        print()

    print(f"Governance summary: {kernel.audit_summary()}")
    print(f"Agent plane:        {plane.status()}")
    print(f"Human protection:   {human.status()}")

if __name__ == "__main__":
    run()
