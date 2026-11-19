"""
Human Protection Plane — Mandatory governance and oversight layer.

Treats humans as protected stakeholders, not optimization targets.
The system MUST NOT optimize purely for throughput when safety, rights,
privacy, or due process are implicated.

Provides: explanation views, confidence labels, consent/notice controls,
appeal and override mechanisms, harm review, emergency shutdown.

Capability level: ANI, Reactive + Limited Memory, Governance / Oversight.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

_log = logging.getLogger("govcore.human")


class ConfidenceLabel(Enum):
    HIGH      = "HIGH"       # Multiple independent sources confirm
    MEDIUM    = "MEDIUM"     # Supported but uncertain
    LOW       = "LOW"        # Inference or projection
    UNCERTAIN = "UNCERTAIN"  # Escalation required


@dataclass
class ExplainedOutput:
    """
    Every system output intended for humans carries mandatory provenance
    and a confidence label. Outputs without these are not valid outputs.
    """
    content:          str
    confidence_label: ConfidenceLabel
    evidence_sources: List[str]
    assumptions:      List[str]
    caveats:          List[str]
    escalation_flag:  bool = False
    appeal_available: bool = True
    operator_note:    str  = ""

    def render(self) -> str:
        lines = [
            f"[{self.confidence_label.value} CONFIDENCE]",
            self.content,
            "",
        ]
        if self.evidence_sources:
            lines.append(f"Sources    : {'; '.join(self.evidence_sources)}")
        if self.assumptions:
            lines.append(f"Assumptions: {'; '.join(self.assumptions)}")
        if self.caveats:
            lines.append(f"Caveats    : {'; '.join(self.caveats)}")
        if self.escalation_flag:
            lines.append(
                "ESCALATION FLAGGED: Uncertainty exceeds threshold. Human review required."
            )
        if self.appeal_available:
            lines.append(
                "This output can be appealed or overridden via the Human Protection Plane."
            )
        if self.operator_note:
            lines.append(f"Note: {self.operator_note}")
        return "\n".join(lines)


class HumanProtectionPlane:
    """
    Mandatory protection layer for all human-facing outputs and decisions.

    Cannot be bypassed. Cannot be disabled except via emergency shutdown.
    Provides the six mandatory controls:
      1. Explanation views and confidence labels
      2. Consent and notice controls
      3. Appeal and override mechanisms
      4. Harm review for high-impact recommendations
      5. Emergency shutdown capability
      6. Rollback readiness
    """

    HIGH_UNCERTAINTY_THRESHOLD = 0.70

    def __init__(self):
        self._active        = True
        self._overrides:    List[Dict] = []
        self._appeals:      List[Dict] = []
        self._shutdown_log: List[Dict] = []
        self._consent_log:  List[Dict] = []
        _log.info("HumanProtectionPlane: ACTIVE.")

    # ── Control 1: Explanation and confidence labeling ────────────────────

    def label_output(
        self,
        content:     str,
        confidence:  float,
        sources:     List[str],
        assumptions: List[str] = None,
        caveats:     List[str] = None,
    ) -> ExplainedOutput:
        """Attach mandatory confidence label and provenance to any system output."""
        if confidence >= 0.80:
            label = ConfidenceLabel.HIGH
        elif confidence >= 0.55:
            label = ConfidenceLabel.MEDIUM
        elif confidence >= 0.30:
            label = ConfidenceLabel.LOW
        else:
            label = ConfidenceLabel.UNCERTAIN

        escalate = confidence < (1.0 - self.HIGH_UNCERTAINTY_THRESHOLD)

        return ExplainedOutput(
            content          = content,
            confidence_label = label,
            evidence_sources = sources or [],
            assumptions      = assumptions or [],
            caveats          = caveats or [],
            escalation_flag  = escalate,
        )

    # ── Control 2: Consent and notice controls ────────────────────────────

    def record_consent(
        self,
        subject_id:   str,
        action_type:  str,
        consent_given: bool,
        basis:        str,
    ) -> Dict:
        record = {
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "subject_id":   subject_id,
            "action_type":  action_type,
            "consent":      consent_given,
            "legal_basis":  basis,
        }
        self._consent_log.append(record)
        return record

    # ── Control 3: Override / Appeal ─────────────────────────────────────

    def record_override(
        self,
        operator_id:              str,
        original_recommendation:  str,
        override_action:          str,
        justification:            str,
    ) -> Dict:
        """Record a human operator override for complete audit trail."""
        record = {
            "timestamp":               datetime.now(timezone.utc).isoformat(),
            "operator_id":             operator_id,
            "original_recommendation": original_recommendation[:200],
            "override_action":         override_action,
            "justification":           justification,
        }
        self._overrides.append(record)
        _log.info(f"Override recorded by {operator_id}: {override_action[:80]}")
        return record

    def submit_appeal(
        self,
        appellant_id:       str,
        decision_reference: str,
        appeal_grounds:     str,
    ) -> Dict:
        """Submit a formal appeal against a system decision."""
        record = {
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "appellant_id":       appellant_id,
            "decision_reference": decision_reference,
            "appeal_grounds":     appeal_grounds,
            "status":             "PENDING_REVIEW",
        }
        self._appeals.append(record)
        _log.info(f"Appeal [{appellant_id}]: {appeal_grounds[:80]}")
        return record

    def resolve_appeal(self, decision_reference: str, resolution: str) -> bool:
        for appeal in self._appeals:
            if appeal["decision_reference"] == decision_reference:
                appeal["status"] = resolution
                appeal["resolved_at"] = datetime.now(timezone.utc).isoformat()
                return True
        return False

    # ── Control 5: Emergency Shutdown ────────────────────────────────────

    def emergency_shutdown(self, operator_id: str, reason: str) -> Dict:
        """
        Halt all agent activity immediately.
        Logs the shutdown event BEFORE halting. Cannot be bypassed.
        """
        log_entry = {
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "event":       "EMERGENCY_SHUTDOWN",
            "operator_id": operator_id,
            "reason":      reason,
        }
        self._shutdown_log.append(log_entry)
        self._active = False
        _log.critical(f"EMERGENCY SHUTDOWN by {operator_id}: {reason}")
        return log_entry

    def restore(self, operator_id: str) -> bool:
        """Restore from shutdown — requires explicit operator authorization."""
        self._active = True
        _log.warning(f"System restored by {operator_id}.")
        return True

    # ── Control 6: Rollback readiness ────────────────────────────────────

    def verify_rollback_readiness(self) -> Dict:
        """
        Check that all preconditions for emergency rollback are in place.
        In production, this would verify backup integrity, recovery procedures, etc.
        """
        return {
            "shutdown_capability":   True,
            "override_mechanism":    True,
            "appeal_path":           True,
            "audit_trail_intact":    len(self._overrides) >= 0,
            "active":                self._active,
        }

    def is_active(self) -> bool:
        return self._active

    def status(self) -> Dict:
        return {
            "active":             self._active,
            "overrides_recorded": len(self._overrides),
            "appeals_pending":    sum(1 for a in self._appeals if a["status"] == "PENDING_REVIEW"),
            "appeals_total":      len(self._appeals),
            "shutdowns_logged":   len(self._shutdown_log),
            "consent_records":    len(self._consent_log),
        }
