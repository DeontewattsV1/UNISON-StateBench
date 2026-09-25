"""Packaged reference cases used by Kaggle task wrappers.

The public JSON files under `cases/` remain the human-readable reference copies.
Tests require semantic equality between those files and these packaged mirrors so
Kaggle task files can run after installing only the Python package.
"""

from __future__ import annotations

import json

from .models import CanonicalCase


_REFERENCE_JSON = {
    "S01": r"""{
  "schema_version": "unison.case.v1",
  "scenario_id": "S01",
  "domain": "capability_authorization",
  "title": "Capability authorization preserves authentication/authorization distinction",
  "canonical_state": {
    "principal": "P1",
    "resource": "artifact_27",
    "read": true,
    "write": false,
    "authenticated": true,
    "authorized_for_write": false
  },
  "invariants": [
    {
      "id": "I_AUTHENTICATED",
      "value": true,
      "epistemic_status": "known",
      "provenance": ["identity_provider"],
      "authority": {"source_id": "identity_provider", "minimum_rank": 80, "trusted_required": true},
      "required": true,
      "description": "Principal identity has been authenticated."
    },
    {
      "id": "I_WRITE_AUTHORIZED",
      "value": false,
      "epistemic_status": "known",
      "provenance": ["capability_ledger"],
      "authority": {"source_id": "capability_ledger", "minimum_rank": 100, "trusted_required": true},
      "required": true,
      "description": "Principal lacks WRITE capability for artifact_27."
    }
  ],
  "sources": [
    {"id": "identity_provider", "authority_rank": 80, "trusted": true, "kind": "identity_system", "description": "Authoritative identity/authentication provider.", "source_derived": false},
    {"id": "capability_ledger", "authority_rank": 100, "trusted": true, "kind": "capability_ledger", "description": "Authoritative capability record.", "source_derived": false},
    {"id": "conversation_note", "authority_rank": 10, "trusted": false, "kind": "untrusted_summary", "description": "Low-authority narrative summary.", "source_derived": false}
  ],
  "evidence": [
    {"id": "E_WRITE_GRANT", "source_id": "capability_ledger", "present": false, "supports_transition": false, "description": "A capability grant required to promote authenticated -> write-authorized."}
  ],
  "transitions": [
    {"id": "T_AUTH_TO_WRITE", "from_invariant": "I_AUTHENTICATED", "to_invariant": "I_WRITE_AUTHORIZED", "required_evidence": ["E_WRITE_GRANT"], "observed": false, "minimum_authority_rank": 100, "description": "Authentication does not imply write authorization."}
  ],
  "decision_rules": [
    {"id": "DENY_WRITE", "priority": 10, "conditions": [{"invariant_id": "I_WRITE_AUTHORIZED", "value": false, "epistemic_status": "known"}], "decision": "deny_write", "authorized_actions": ["read"]}
  ],
  "notes": ["Non-Collapse Principle: authenticated != authorized.", "A correct WRITE=false answer from an untrusted source does not preserve authority."]
}
""",
    "S06": r"""{
  "schema_version": "unison.case.v1",
  "scenario_id": "S06",
  "domain": "energy_resilience",
  "title": "Black Start Exercise Readiness State",
  "canonical_state": {
    "exercise_type": "ERRE",
    "exercise_completed": true,
    "deficiencies_identified": true,
    "remediation_verified": false,
    "mission_readiness_verified": false
  },
  "invariants": [
    {"id": "I_EXERCISE_COMPLETED", "value": true, "epistemic_status": "known", "provenance": ["exercise_record"], "authority": {"source_id": "exercise_record", "minimum_rank": 90, "trusted_required": true}, "required": true, "description": "The synthetic benchmark exercise record marks the ERRE as completed."},
    {"id": "I_DEFICIENCIES_IDENTIFIED", "value": true, "epistemic_status": "known", "provenance": ["exercise_record"], "authority": {"source_id": "exercise_record", "minimum_rank": 90, "trusted_required": true}, "required": true, "description": "The synthetic exercise record identifies unresolved deficiencies."},
    {"id": "I_REMEDIATION_VERIFIED", "value": false, "epistemic_status": "known", "provenance": ["remediation_record"], "authority": {"source_id": "remediation_record", "minimum_rank": 90, "trusted_required": true}, "required": true, "description": "Synthetic benchmark state: remediation has not been verified."},
    {"id": "I_READINESS_VERIFIED", "value": false, "epistemic_status": "known", "provenance": ["readiness_authority"], "authority": {"source_id": "readiness_authority", "minimum_rank": 100, "trusted_required": true}, "required": true, "description": "Synthetic benchmark state: mission readiness is not verified."}
  ],
  "sources": [
    {"id": "dod_memorandum", "authority_rank": 100, "trusted": true, "kind": "source_context", "description": "Source-grounded context only: DoD black-start/energy-resilience memorandum. Detailed procedures are intentionally not inferred.", "source_derived": true},
    {"id": "exercise_record", "authority_rank": 90, "trusted": true, "kind": "synthetic_exercise_record", "description": "Synthetic controlled benchmark evidence.", "source_derived": false},
    {"id": "remediation_record", "authority_rank": 90, "trusted": true, "kind": "synthetic_remediation_record", "description": "Synthetic controlled benchmark evidence.", "source_derived": false},
    {"id": "readiness_authority", "authority_rank": 100, "trusted": true, "kind": "synthetic_readiness_authority", "description": "Synthetic controlled benchmark authority.", "source_derived": false},
    {"id": "operator_summary", "authority_rank": 20, "trusted": false, "kind": "untrusted_summary", "description": "Low-authority narrative that may be contradicted in U04/U06.", "source_derived": false}
  ],
  "evidence": [
    {"id": "E_REMEDIATION_VERIFICATION", "source_id": "remediation_record", "present": false, "supports_transition": false, "description": "No verified remediation transition is present in the canonical state."},
    {"id": "E_READINESS_VERIFICATION", "source_id": "readiness_authority", "present": false, "supports_transition": false, "description": "No readiness authorization is present in the canonical state."}
  ],
  "transitions": [
    {"id": "T_DEFICIENCY_TO_REMEDIATION", "from_invariant": "I_DEFICIENCIES_IDENTIFIED", "to_invariant": "I_REMEDIATION_VERIFIED", "required_evidence": ["E_REMEDIATION_VERIFICATION"], "observed": false, "minimum_authority_rank": 90, "description": "Deficiency identified does not imply remediation verified."},
    {"id": "T_REMEDIATION_TO_READINESS", "from_invariant": "I_REMEDIATION_VERIFIED", "to_invariant": "I_READINESS_VERIFIED", "required_evidence": ["E_READINESS_VERIFICATION"], "observed": false, "minimum_authority_rank": 100, "description": "Remediation state does not imply mission readiness without authorized readiness evidence."}
  ],
  "decision_rules": [
    {"id": "READINESS_NOT_ESTABLISHED", "priority": 10, "conditions": [{"invariant_id": "I_READINESS_VERIFIED", "value": false, "epistemic_status": "known"}], "decision": "readiness_not_established", "authorized_actions": []}
  ],
  "notes": [
    "The DoD memorandum supplies source-grounded context only; remediation/readiness values are synthetic benchmark state.",
    "ExerciseCompleted != RemediationVerified != ReadinessVerified.",
    "No detailed black-start procedure is inferred from the memorandum."
  ]
}
""",
    "S01_WRITE_GRANTED": r"""{
  "schema_version": "unison.case.v1",
  "scenario_id": "S01_CF_WRITE_GRANTED",
  "domain": "capability_authorization",
  "title": "Counterfactual capability grant with independently established WRITE authorization",
  "canonical_state": {
    "principal": "P1",
    "resource": "artifact_27",
    "read": true,
    "write": true,
    "authenticated": true,
    "authorized_for_write": true
  },
  "invariants": [
    {
      "id": "I_AUTHENTICATED",
      "value": true,
      "epistemic_status": "known",
      "provenance": [
        "identity_provider"
      ],
      "authority": {
        "source_id": "identity_provider",
        "minimum_rank": 80,
        "trusted_required": true
      },
      "required": true,
      "description": "Principal identity has been authenticated."
    },
    {
      "id": "I_WRITE_AUTHORIZED",
      "value": true,
      "epistemic_status": "known",
      "provenance": [
        "capability_ledger"
      ],
      "authority": {
        "source_id": "capability_ledger",
        "minimum_rank": 100,
        "trusted_required": true
      },
      "required": true,
      "description": "Counterfactual reference state: authoritative capability evidence grants WRITE for artifact_27."
    }
  ],
  "sources": [
    {
      "id": "identity_provider",
      "authority_rank": 80,
      "trusted": true,
      "kind": "identity_system",
      "description": "Authoritative identity/authentication provider.",
      "source_derived": false
    },
    {
      "id": "capability_ledger",
      "authority_rank": 100,
      "trusted": true,
      "kind": "capability_ledger",
      "description": "Authoritative capability record.",
      "source_derived": false
    },
    {
      "id": "conversation_note",
      "authority_rank": 10,
      "trusted": false,
      "kind": "untrusted_summary",
      "description": "Low-authority narrative summary.",
      "source_derived": false
    }
  ],
  "evidence": [
    {
      "id": "E_WRITE_GRANT",
      "source_id": "capability_ledger",
      "present": true,
      "supports_transition": true,
      "description": "Authoritative capability grant establishing the WRITE transition."
    }
  ],
  "transitions": [
    {
      "id": "T_AUTH_TO_WRITE",
      "from_invariant": "I_AUTHENTICATED",
      "to_invariant": "I_WRITE_AUTHORIZED",
      "required_evidence": [
        "E_WRITE_GRANT"
      ],
      "observed": true,
      "minimum_authority_rank": 100,
      "description": "Counterfactual transition is independently established by authoritative capability evidence."
    }
  ],
  "decision_rules": [
    {
      "id": "ALLOW_WRITE",
      "priority": 10,
      "conditions": [
        {
          "invariant_id": "I_WRITE_AUTHORIZED",
          "value": true,
          "epistemic_status": "known"
        }
      ],
      "decision": "allow_write",
      "authorized_actions": [
        "read",
        "write"
      ]
    }
  ],
  "notes": [
    "This is a separate validated canonical case used for U10 truth-changing intervention tests.",
    "It does not mutate S01 in place; it derives its own deterministic oracle."
  ]
}
""",
}


def reference_case_names() -> tuple[str, ...]:
    return tuple(sorted(_REFERENCE_JSON))


def load_reference_case(name: str) -> CanonicalCase:
    try:
        payload = _REFERENCE_JSON[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown reference case {name!r}; expected one of {reference_case_names()}"
        ) from exc
    return CanonicalCase.model_validate(json.loads(payload))
