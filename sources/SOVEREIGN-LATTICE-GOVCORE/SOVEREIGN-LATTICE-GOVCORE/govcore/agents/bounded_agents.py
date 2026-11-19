"""
Agent Plane — The "Propose and Coordinate" Layer.

Bounded agents: Retrieval, Verification, Policy, Risk,
Cyber Defense, PQC Migration, Audit.

Agents MAY: observe, retrieve, summarize, simulate, recommend.
Agents MAY NOT: take irreversible action without human authorization.

Capability level: AGI-precursor (max), Limited Memory, Agentic (bounded).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

_log = logging.getLogger("govcore.agents")


class AgentType(Enum):
    RETRIEVAL     = "retrieval"
    VERIFICATION  = "verification"
    POLICY        = "policy"
    RISK          = "risk"
    CYBER_DEFENSE = "cyber_defense"
    PQC_MIGRATION = "pqc_migration"
    AUDIT         = "audit"


@dataclass
class AgentRecommendation:
    """
    Every agent output is a recommendation, never a command.
    Agents propose; humans command.
    """
    agent_type:              AgentType
    action:                  str
    evidence:                str
    expected_effect:         str
    risks:                   str
    alternative:             str
    confidence:              float
    requires_human_approval: bool
    created_at:              str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    supporting_data: Dict = field(default_factory=dict)

    def format_for_operator(self) -> str:
        approval_tag = "[REQUIRES HUMAN APPROVAL]" if self.requires_human_approval else "[ADVISORY]"
        parts = [
            f"{approval_tag} - {self.agent_type.value.upper()} AGENT",
            f"Recommended action : {self.action}",
            f"Evidence           : {self.evidence}",
            f"Expected effect    : {self.expected_effect}",
            f"Risks              : {self.risks}",
            f"Alternative        : {self.alternative}",
            f"Confidence         : {self.confidence:.0%}",
        ]
        return "\n".join(parts)


class BoundedAgent:
    """Base class for all bounded agents in the Agent Plane."""

    def __init__(self, agent_type: AgentType, action_budget: int = 50):
        self.agent_type      = agent_type
        self.action_budget   = action_budget
        self._actions_taken  = 0
        self._session_token: Optional[str] = None
        self._log = logging.getLogger(f"govcore.agents.{agent_type.value}")

    def is_authorized(self) -> bool:
        return (
            self._session_token is not None
            and self._actions_taken < self.action_budget
        )

    def authenticate(self, session_token: str) -> None:
        """Ephemeral credential — scoped to this session only."""
        self._session_token = session_token
        self._actions_taken = 0

    def _consume_budget(self, count: int = 1) -> bool:
        if self._actions_taken + count > self.action_budget:
            self._log.warning(
                f"{self.agent_type.value}: budget exhausted, re-authorization required."
            )
            return False
        self._actions_taken += count
        return True


class WatchfloorAgent(BoundedAgent):
    """
    Continuously monitors network telemetry and threat feeds.
    Produces ranked triage recommendations — does NOT act on findings.
    Surfaces results for human review.
    """

    def __init__(self):
        super().__init__(AgentType.CYBER_DEFENSE, action_budget=100)

    def triage(
        self,
        telemetry_events: List[Dict],
        threat_feeds: List[Dict] = None,
    ) -> List[AgentRecommendation]:
        if not self.is_authorized():
            self._log.error("WatchfloorAgent: not authorized.")
            return []
        if not self._consume_budget(len(telemetry_events)):
            return []

        threat_feeds = threat_feeds or []
        recommendations = []

        for event in telemetry_events:
            severity = float(event.get("severity", 0.0))
            if severity >= 0.7:
                recommendations.append(AgentRecommendation(
                    agent_type=self.agent_type,
                    action=f"Investigate anomaly: {event.get('description', 'unknown')}",
                    evidence=f"Severity={severity:.2f}, source={event.get('source', 'telemetry')}",
                    expected_effect="Identify threat vector and containment options.",
                    risks="Delay may allow lateral movement.",
                    alternative="Alert-only mode pending manual investigation.",
                    confidence=min(0.95, severity),
                    requires_human_approval=severity >= 0.9,
                    supporting_data=event,
                ))

        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        return recommendations


class PQCMigrationAgent(BoundedAgent):
    """
    Inventories cryptographic dependencies and produces migration sequence recommendations.
    Prioritizes by sensitivity and PQC sequencing rules (long-lived secrets first).
    Does NOT execute migrations.
    """

    MIGRATION_SEQUENCE = [
        "root_ca_certificates",
        "long_lived_secrets",
        "inter_service_trust",
        "model_signing_keys",
        "audit_log_signing",
        "short_lived_tokens",
        "session_keys",
    ]

    def __init__(self):
        super().__init__(AgentType.PQC_MIGRATION, action_budget=200)

    def assess_readiness(self, crypto_inventory: List[Dict]) -> List[AgentRecommendation]:
        """Assess PQC migration readiness from a cryptographic inventory."""
        if not self.is_authorized():
            return []
        if not self._consume_budget():
            return []

        recommendations = []
        for item in crypto_inventory:
            algo        = item.get("algorithm", "")
            sensitivity = item.get("sensitivity", "standard")
            use         = item.get("use", "")

            vulnerable = any(v in algo for v in ("RSA", "ECDH", "ECDSA", "DSA", "DH"))
            if vulnerable:
                priority = "HIGH" if sensitivity == "critical" else "MEDIUM"
                target   = "ML-KEM (FIPS 203)" if "key" in use else "ML-DSA (FIPS 204)"

                recommendations.append(AgentRecommendation(
                    agent_type=self.agent_type,
                    action=f"Migrate {item.get('name', 'component')} from {algo} to {target}",
                    evidence=f"{algo} vulnerable to Shor's algorithm. Priority: {priority}.",
                    expected_effect=f"Post-quantum protection via {target}.",
                    risks="Migration requires testing. Schedule during maintenance window.",
                    alternative="Hybrid classical+PQC approach during transition.",
                    confidence=0.92 if priority == "HIGH" else 0.78,
                    requires_human_approval=True,
                    supporting_data={
                        "priority": priority,
                        "algorithm": algo,
                        "target": target,
                        "component_class": item.get("component_class", ""),
                    },
                ))

        # Sort by migration sequence priority (long-lived secrets first)
        def seq_rank(rec: AgentRecommendation) -> int:
            component_class = rec.supporting_data.get("component_class", "")
            for i, cls in enumerate(self.MIGRATION_SEQUENCE):
                if cls in component_class.lower():
                    return i
            return len(self.MIGRATION_SEQUENCE)

        recommendations.sort(key=seq_rank)
        return recommendations


class SupplyChainIntegrityAgent(BoundedAgent):
    """
    Traces chips, model weights, SBOMs, and deployment attestations.
    Flags discrepancies for human review — does not modify supply chain records.
    """

    def __init__(self):
        super().__init__(AgentType.VERIFICATION, action_budget=500)

    def audit_component(self, component: Dict) -> Optional[AgentRecommendation]:
        """Audit a single supply chain component. Returns None if clean."""
        if not self.is_authorized():
            return None
        if not self._consume_budget():
            return None

        flags = []
        if not component.get("provenance_attestation"):
            flags.append("Missing provenance attestation")
        if not component.get("signing_key_fingerprint"):
            flags.append("Unsigned component")
        if component.get("attestation_expired", False):
            flags.append("Provenance attestation expired")

        if not flags:
            return None

        return AgentRecommendation(
            agent_type=self.agent_type,
            action=f"Review component: {component.get('name', 'unknown')} — {'; '.join(flags)}",
            evidence=f"Supply chain audit flags: {flags}",
            expected_effect="Resolve provenance gaps before deployment.",
            risks="Unverified components may introduce supply chain compromise.",
            alternative="Quarantine component until provenance is confirmed.",
            confidence=0.88,
            requires_human_approval=True,
            supporting_data={"flags": flags, "component": component},
        )


class AuditAgent(BoundedAgent):
    """
    Maintains append-only audit trail for all agent actions and recommendations.
    """

    def __init__(self):
        super().__init__(AgentType.AUDIT, action_budget=10_000)
        self._ledger: List[Dict] = []

    def log_event(
        self, event_type: str, agent: str, summary: str, metadata: Dict = None
    ) -> Dict:
        entry = {
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent":      agent,
            "summary":    summary,
            "metadata":   metadata or {},
            "seq":        len(self._ledger),
        }
        self._ledger.append(entry)
        return entry

    def get_ledger(self, agent_filter: Optional[str] = None) -> List[Dict]:
        if agent_filter:
            return [e for e in self._ledger if e["agent"] == agent_filter]
        return list(self._ledger)

    def verify_completeness(self) -> Dict:
        """Basic ledger integrity check — seq numbers must be contiguous."""
        if not self._ledger:
            return {"valid": True, "entries": 0}
        seqs = [e["seq"] for e in self._ledger]
        expected = list(range(len(self._ledger)))
        valid = seqs == expected
        return {
            "valid":   valid,
            "entries": len(self._ledger),
            "gaps":    [] if valid else [i for i, s in enumerate(seqs) if s != expected[i]],
        }


class AgentPlane:
    """
    Orchestrator for all bounded agents.
    All agents operate under ephemeral credentials and action budgets.
    No agent may take irreversible action without human authorization.
    """

    def __init__(self):
        self.watchfloor    = WatchfloorAgent()
        self.pqc           = PQCMigrationAgent()
        self.supply_chain  = SupplyChainIntegrityAgent()
        self.audit         = AuditAgent()
        self._agents = {
            AgentType.CYBER_DEFENSE: self.watchfloor,
            AgentType.PQC_MIGRATION: self.pqc,
            AgentType.VERIFICATION:  self.supply_chain,
            AgentType.AUDIT:         self.audit,
        }
        _log.info(f"AgentPlane initialized — {len(self._agents)} agents ready.")

    def authorize_all(self, session_token: str) -> None:
        """Authorize all agents for this session with scoped tokens."""
        for agent_type, agent in self._agents.items():
            scoped = hashlib.sha256(
                f"{session_token}:{agent_type.value}".encode()
            ).hexdigest()
            agent.authenticate(scoped)

    def status(self) -> Dict:
        return {
            a.agent_type.value: {
                "authorized":   a.is_authorized(),
                "budget_used":  a._actions_taken,
                "budget_total": a.action_budget,
            }
            for a in self._agents.values()
        }
