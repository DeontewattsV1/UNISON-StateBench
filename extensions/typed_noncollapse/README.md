# Typed Non-Collapse Extension (experimental)

> **Status:** post-v0.1 research extension. This directory is **not** part of the frozen UNISON-StateBench v0.1 corpus, source revision, 162-call empirical matrix, or primary leaderboard metrics.

The constitutional engineering axiom is:

```text
Preserve the relation type, not merely the value.
```

Protected distinctions include:

```text
same value != same relation
same invariant != same state
same orbit != reachable state
same output != same internal viability
saturation != failure
symmetry != robustness
False != Unknown
```

The governing bridge rule is:

```text
R_i(x, y) does not imply R_j(x, y), i != j
```

unless an explicit bridge certificate supplies the evidence required for that cross-type inference.

## Certificate vector

The extension keeps the certificate vector factored:

```text
C_U = [C_I, C_Q, C_R, C_V, C_A, C_ANTAGONISM?]
```

Each coordinate is thresholded independently. Scenario pass/fail is policy over the vector; there is no scalar "Unison score."

## AP-REL-01

`AP-REL-01` checks that invariant equivalence plus a transformation edge do not license isolated one-body reachability:

```text
~I + <->T  !=>  ~>_(tau, isolated:1->1)
```

The fixture keeps electric-charge conservation as an obstruction and represents a hypothetical admissible `1->1` process certificate as the missing bridge evidence. A separate multi-body reaction may not be substituted for the named process signature.

Diagnostic: `REL.I_T_TO_REACH`.

## AP-SAT-01

For the saturated antagonist example with

```text
x0 = 1
g = 2
y_min = -1
y_max = 1
epsilon_x = 0.35
```

the static input bands are:

```text
B_perfect = [-1.0, 3.0]
B_viable  = [-1.35, 3.35]
```

Saturation therefore marks loss of perfect absorption, not automatic loss of viability.

No input trajectory `u(t)` is supplied, so numerical event times `tau_sat` and `tau_exit` are not derivable. Their equality remains `UNKNOWN`, preserving `False != Unknown`.

Diagnostics: `BND.SAT_EQ_EXIT` and `BND.TIME_WITHOUT_TRAJECTORY`.

## Integration boundary

- `benchmark/oracle.py` gains `derive_typed_oracle()` without changing `derive_oracle()`.
- `benchmark/state_collapse.py` gains typed collapse kinds and `detect_typed_state_collapses()` without changing the frozen detector's semantics.
- Typed failures reuse `StateCollapseReport`, so SCR remains the headline state-collapse metric.
- The extension does not alter U01-U10 or `cases/v0.1-corpus.json`.

Novelty and empirical validity are not established by these fixtures. They are adversarial reasoning tests for typed relation preservation.
