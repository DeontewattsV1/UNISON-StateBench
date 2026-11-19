# UNISON-StateBench v0.1 empirical run

The empirical phase is pinned to frozen source revision:

`df10125d05f8271c613213851214ad8d37554363`

Before constructing or executing any trial, `empirical.freeze.verify_frozen_workspace()`
checks the Git blob identity of all S01-S10 baseline fixtures, the frozen S01 U10
counterfactual, the v0.1 corpus manifest, and the constitutional core.

Generate the exact trial matrix:

```bash
python scripts/build_v01_matrix.py
```

The v0.1 plan contains **162 model calls per model**:

- U01: 50 — 10 scenarios x 5 representations
- U02: 10 — order invariance
- U03: 10 — deterministic paraphrase
- U04: 10 — contradiction
- U05: 10 — missing evidence
- U06: 10 — authority conflict
- U07: 10 — principal-isolation canary
- U08: 10 — tool-state integrity
- U09: 40 — 10 scenarios x 4 distance conditions
- U10: 2 — the frozen S01 baseline/counterfactual pair

U10 is intentionally not expanded after the source freeze. Creating nine additional
truth-changing counterfactual cases would change the experimental object.

## Model lineup

Do not guess Kaggle model identifiers. In the execution notebook, snapshot:

```python
list(kbench.llms.keys())
```

Then pass the exact selected keys to:

```python
from empirical.kaggle_runner import run_lineup
run_lineup(
    kbench,
    model_keys=SELECTED_EXACT_KEYS,
    output_dir="raw-results",
    run_id="unison-v0.1-001",
)
```

The runner refuses unavailable model keys and records the full availability snapshot.
Each completed model call is fsync'd to append-only JSONL before the next call begins.

Primary outputs remain eight separate metrics: IPR, RCR, CRR, FHR, CAL, PLR, AIR, SCR.
There is no composite score.

Confidence intervals use a deterministic 95% scenario-cluster percentile bootstrap
(default 10,000 resamples, seed 1729). Resampling whole scenarios preserves dependence
among representations, mutations, distance conditions, and the S01 U10 pair.
