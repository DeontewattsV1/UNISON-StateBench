# UNISON-StateBench
    Deterministic benchmark for invariant, provenance, authority, epistemic-state, and operational-state preservation in AI systems
UNISON-StateBench v0.1

> **Naming:** UNISON is the underlying research/framework identity. UNISON-StateBench is the public benchmark artifact and implementation.

UNISON-StateBench evaluates whether an AI system preserves explicitly defined invariants across representation changes, provenance/authority conflicts, missing evidence, and state transitions.

Frozen constitutional core

A canonical invariant is typed as:

I_k = (value, epistemic_status, provenance, authority)

UNISON keeps three properties distinct:

• Consistency: outputs agree across representations.
• Correctness: outputs agree with the deterministic oracle.
• State preservation: outputs do not collapse distinct operational or epistemic states.

The Non-Collapse Principle is first-class:

A -> B -> C does not imply A => C unless required transition evidence exists.

False != Unknown is enforced as an epistemic invariant.

Implemented gates

Gate 1 — canonical truth + oracle

• immutable canonical models and typed epistemic state
• provenance/authority/evidence/transition types
• deterministic oracle derivation
• state-collapse detection
• canonical/oracle integrity hashing
• S01 capability-authorization fixture
• S06 energy-resilience-readiness fixture
• non-collapse and integrity tests

Gate 2 — deterministic representation + guarded mutation

Five deterministic renderers are implemented:

• prose
• JSON
• dependency-free YAML
• pipe table
• event log

Six presentation-only mutation families are implemented:

• reorder
• controlled paraphrase
• contradiction injection
• missing evidence
• lower-authority conflict
• adversarial value flip

Every public renderer and mutation is wrapped by the integrity guard. The guard snapshots both the canonical case and its deterministic oracle before execution and verifies both again afterward, including when transform code raises an exception.

Presentation views are additionally bound to their origin with case_digest and oracle_digest, preventing a view generated from one case from being rendered or mutated as though it belonged to another.

Constitutional invariant

Renderer and mutation code may transform a detached EvidenceView. They may never mutate CanonicalCase or its deterministic oracle.

Formally:

CanonicalOracle_before == CanonicalOracle_after(renderer/mutation)

A presentation mutation is not an oracle-changing experimental intervention. If a later U10 trial needs the reference truth itself to change, it must construct a separate validated canonical case and derive a separate oracle rather than rewriting the source case in place.

Example

from benchmark.loaders import load_case
from benchmark.presentation import build_evidence_view
from benchmark.mutations import inject_authority_conflict
from benchmark.renderers import render_json

case = load_case("cases/S06_black_start_resilience.json")
view = build_evidence_view(case)
mutated = inject_authority_conflict(
    case,
    view,
    invariant_id="I_REMEDIATION_VERIFIED",
    lower_source_id="operator_summary",
    conflicting_value=True,
)
artifact = render_json(case, mutated)
print(artifact.content)

Install and run

python -m pip install -e '.[dev]'
pytest
