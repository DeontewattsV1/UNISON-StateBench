# Scientific admissibility framework

This document is the single evidence framework for everything in this repository, including the repositories imported under `sources/`. It does not establish that any claim is true. It defines what a claim must carry before it may be *promoted* to a stronger status, and how each promotion is recorded.

## 1. Backbone: the UNISON drafts

The framework is assembled from the owner's individual working drafts on the IETF datatracker (rev -01, October 2026). None is an IETF standard or has had IETF review; they are cited as the design source, not as authority.

| Draft | Concept used here |
|---|---|
| draft-watts-scientific-admissibility; draft-watts-scientific-admissibility-evidence | Evidence record fields for bounded claims, preregistered procedures, admissibility evaluations, provenance artifacts and integrity metadata. Integrity, schema conformance, admissibility, governance and truth are kept as **separate** properties. |
| draft-watts-research-evidence-envelope | Versioned envelope for claim, source provenance, evidence class, uncertainty, falsifiers, replication procedure and artifact hashes. |
| draft-watts-claim-promotion-receipts | A receipt for every explicit promotion across an evidence or authority boundary, so raw observations or unreviewed outputs are never silently retyped as authoritative state. |
| draft-watts-verification-promotion-boundaries; draft-watts-gov-verification-promotion-boundaries | Ordered stages REGISTERED → SPEC_VALIDATED → LOCAL_CONFORMANT → INDEPENDENTLY_REPRODUCED → SECURITY_TESTED → RELEASE_ELIGIBLE. A lower stage never implies a higher one. Unknown evidence never promotes. Subject evidence and verifier evidence are distinguished. |
| draft-watts-unison-state-preservation | Value, epistemic status, provenance and authority are separate fields; a non-collapse rule governs operational and epistemic transitions. |
| draft-watts-unison-noncollapse | Bounded correspondence among representations, and explicit promotion boundaries between observation, evidence, authorization and execution. |

## 2. Core rules

1. **Typed state.** Every claim carries `(value, epistemic_status, provenance, authority)`. A new claim starts at `epistemic_status = unknown`, `value = null`.
2. **No silent promotion (non-collapse).** A change of status is valid only if it is produced by a named transition whose preconditions are satisfied and which emits a promotion receipt. `unknown → known` without a transition is a *collapse* and blocks promotion (implemented in `benchmark/state_collapse.py`).
3. **Separation of properties.** A valid hash proves integrity of bytes, not correctness. A schema-valid record is well-formed, not admissible. An admissible record is eligible for evaluation, not true. A governance approval authorizes an action, not a scientific conclusion.
4. **Verification ladder.** Status levels used in this repository, lowest to highest:
   `concept` → `defined` → `implemented` → `locally_tested` → `independently_reproduced` → `security_tested` → `release_eligible`. Empirical claims add `preregistered` → `measured` → `replicated`.
   Each step needs its own evidence. `locally_tested` is the highest status any item in this repository currently holds.
5. **Falsifiability.** An empirical claim is admissible only if its record names a falsification criterion and the data it would be tested on (see `docs/FUTURE_WORK.md`).
6. **Novelty.** Defining a term does not demonstrate novelty. Every item in the claims register is marked *not assessed against prior work* unless a prior-work search is cited.
7. **Hash chaining.** Each step's output is hashed (SHA-256 over canonical JSON) and chained with the previous step's link hash, so any later edit is detectable (`playground/src/pipeline.js` `verifyChain`).
8. **Scenario separation.** Simulated or scenario outputs cannot be promoted to established fact (GovCore RULE-003 TEMPORAL_SEPARATION, enforced in the playground governance stage).

## 3. Evidence record

All future experiments and artifacts fill in [`schemas/evidence-record.schema.json`](../schemas/evidence-record.schema.json). Required fields: `claim`, `status`, `method`, `inputs_hash`, `outputs_hash`, `code_commit`, `promotion_receipt`. An example is in [`schemas/examples/evidence-record.example.json`](../schemas/examples/evidence-record.example.json).

## 4. How each repository maps onto the framework

| Framework element | Mechanism | Repository |
|---|---|---|
| Typed invariants, oracle, collapse detection | `benchmark/models.py`, `oracle.py`, `state_collapse.py`, `typed_noncollapse.py` | UNISON-StateBench |
| Evidence windows (all expected observers must report SATISFIED; missing → UNVERIFIABLE) | `capability-gateway/src/auth/evidence.ts` | AGI-CP |
| Fail-closed gate, revocation, signed receipts | `capability-gateway/`, `tract/` | AGI-CP |
| Requirement ↔ evidence linking | RTM documents (concept) | traceability-matrix |
| Governance gate (operating mode, approval, escalation) | `govcore/governance/kernel.py` | SOVEREIGN-LATTICE-GOVCORE |
| Policy validation, event → action runtime, manifest verification, tamper testing | `policy_schema.py`, `orchestrator.py`, `manifest_verifier.py`, `tamper_tester.py` | Linguistic-Encryption-System-Celestial- (and private phaseform_runtime_package_v6) |
| Reversible encoding transform with round-trip check | `celestial_agent/celestial_language.py` | Linguistic-Encryption-System-Celestial- |
| Advisory state-space visual (never evidence) | `recognitive-field-v3.html` field dynamics | Recognitive-field |
| Encoded command transport and sandboxed execution | `celestial_core.py` | celestial_agent_desktop_upgrade |
| Framing concepts | documents | AISoulFrameworkConcepts |

## 5. Promotion receipt (minimum content)

`claim_id`, `from_status`, `to_status`, `transition` (named), `evidence_refs` (hashes), `checks` (each with pass/fail), `blocking_steps`, `chain_head`, `issued_at`, `issuer`. A receipt with any failed implemented check must not raise the status. The playground emits a demonstration receipt of this form.

## 6. Known limits

- The playground's `locally_supported` outcome is a demonstration on a synthetic sample; it is not a scientific result.
- No independent reproduction of any mechanism in this repository has been recorded yet.
- The drafts are working documents; field names here may change when the drafts change.
