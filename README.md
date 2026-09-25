# UNISON-StateBench v0.1

> **Naming:** UNISON is the underlying research/framework identity. UNISON-StateBench is the public benchmark artifact and implementation.

UNISON-StateBench evaluates whether an AI system preserves explicitly defined invariants across representation changes, provenance/authority conflicts, missing evidence, and state transitions.

## Frozen constitutional core

A canonical invariant is typed as:

`I_k = (value, epistemic_status, provenance, authority)`

UNISON keeps three properties distinct:

- **Consistency**: outputs agree across representations.
- **Correctness**: outputs agree with the deterministic oracle.
- **State preservation**: outputs do not collapse distinct operational or epistemic states.

The Non-Collapse Principle is first-class:

`A -> B -> C` does **not** imply `A => C` unless required transition evidence exists.

`False != Unknown` is enforced as an epistemic invariant.

## Implemented gates

### Gate 1 — canonical truth + oracle

- immutable canonical models and typed epistemic state
- provenance/authority/evidence/transition types
- deterministic oracle derivation
- state-collapse detection
- canonical/oracle integrity hashing
- S01 capability-authorization fixture
- S06 energy-resilience-readiness fixture
- non-collapse and integrity tests

### Gate 2 — deterministic representation + guarded mutation

Five deterministic renderers are implemented:

- prose
- JSON
- dependency-free YAML
- pipe table
- event log

Six presentation-only mutation families are implemented:

- reorder
- controlled paraphrase
- contradiction injection
- missing evidence
- lower-authority conflict
- adversarial value flip

Every public renderer and mutation is wrapped by the integrity guard. The guard snapshots both the canonical case and its deterministic oracle before execution and verifies both again afterward, including when transform code raises an exception.

Presentation views are additionally bound to their origin with `case_digest` and `oracle_digest`, preventing a view generated from one case from being rendered or mutated as though it belonged to another.

## Constitutional invariant

Renderer and mutation code may transform a detached **EvidenceView**. They may never mutate `CanonicalCase` or its deterministic oracle.

Formally:

`CanonicalOracle_before == CanonicalOracle_after(renderer/mutation)`

A presentation mutation is **not** an oracle-changing experimental intervention. If a later U10 trial needs the reference truth itself to change, it must construct a separate validated canonical case and derive a separate oracle rather than rewriting the source case in place.

## Example

```python
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
```

## Install and run

```bash
python -m pip install -e '.[dev]'
pytest
```

## Gate 3 — deterministic scoring + trial generation

The pre-Kaggle evaluation layer is implemented before any U01–U10 task wrapper is allowed to depend on it.

Deterministic primary metrics:

• IPR — Invariant Preservation Rate: full-credit preservation requires value + epistemic status + provenance + authority.
• RCR — Representation Correspondence Rate: pairwise semantic-output correspondence inside representation-equivalent trial groups.
• CRR — Contradiction Recognition Rate.
• FHR — False Harmonization Rate: missed contradiction plus adoption of a conflicting invariant/decision/action state.
• CAL — Correct Abstention Level: missing evidence must remain UNKNOWN/ABSENT rather than collapsing to a guessed value.
• PLR — Principal Leakage Rate using explicit forbidden-invariant canaries.
• AIR — Authorization Integrity Risk from actions outside the deterministic authorized-action set.
• SCR — State Collapse Rate from explicit workflow and epistemic boundaries.

Trial generation is deterministic from:

CanonicalCase × Representation × MutationPlan

A trial expectation is separate from the immutable canonical oracle. This is essential for missing-evidence tests: removing presented evidence can make the justified observation UNKNOWN without rewriting canonical truth. The canonical case and canonical oracle hashes remain unchanged.

The five representation values are prose, JSON, YAML, table, and event_log. MutationPlan is presentation-only and supports none, reorder, paraphrase, contradiction, missing evidence, authority conflict, and adversarial corruption. A truth-changing U10 intervention is deliberately not a MutationPlan; it must construct a separate validated CanonicalCase and derive a new oracle.

Acceptance gate:

```text
36 tests passed
python -m compileall benchmark tasks analysis tests
```

The scoring path also treats presentation-induced UNKNOWN/ABSENT states as
epistemic boundaries for SCR. A model does not escape State Collapse Rate merely
because the canonical oracle knew a value before the trial intentionally removed
the evidence needed to justify that value.

## Next gate

Only after Gate 3 passes should U01–U10 Kaggle task wrappers be layered on top.
The next implementation boundary is the Kaggle adapter layer; the canonical models,
trial generator, and deterministic metrics remain framework-independent.
