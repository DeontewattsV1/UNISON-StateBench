---
name: unison-empirical
description: Execute or inspect the frozen UNISON-StateBench v0.1 empirical workflow on Kaggle. Use when the user asks to snapshot Kaggle benchmark models, freeze a model lineup, run UNISON model trials, retrieve raw results, or analyze UNISON empirical outputs.
---

Use the bundled `kaggle` MCP server for live Kaggle access.

## Constitutional boundary

Treat these as immutable scientific identifiers:

- frozen source revision: `df10125d05f8271c613213851214ad8d37554363`
- frozen plan digest: `e1818b8a62d207fbce204b542a1c90e6d0525d223dc4e98a996b0c5e215d8619`
- model calls per model: `162`
- primary metrics: `IPR, RCR, CRR, FHR, CAL, PLR, AIR, SCR`
- composite score: none

Never modify the frozen corpus, canonical oracle, protected source revision, or trial-plan semantics during an empirical run.

## Required workflow

1. Ensure Kaggle MCP authorization is active. Prefer Kaggle OAuth. Never ask the user to paste a Kaggle token into chat.
2. Use Kaggle notebook/benchmark tools to operate the UNISON benchmark execution notebook.
3. First produce only `runtime-snapshot.json`.
4. Verify that the snapshot binds the frozen source revision and frozen plan digest above.
5. Report the exact available model keys from the snapshot. Never infer, normalize, alias, or substitute model identifiers.
6. Freeze an exact lineup only from keys present in the captured runtime snapshot.
7. Before any model calls, report:
   - snapshot digest
   - exact selected model keys
   - model count N
   - expected call count `162 * N`
   - lineup digest
8. Model execution is a separate state transition. Do not start the `162N` calls merely because a snapshot or lineup exists. Require an explicit user request to execute the empirical run.
9. During execution, preserve per-model append-only raw JSONL observations and the results manifest. Do not silently retry into a different model or merge different lineups.
10. Do not compute publication metrics from incomplete model result files. Each selected model must have exactly 162 unique successful plan IDs and no execution errors.
11. After complete results exist, compute the eight metrics separately, scenario-cluster confidence intervals, U09 distance behavior, and failure topology.
12. Do not introduce or report a single composite leaderboard score.

## Kaggle tool use

Kaggle's official MCP server may expose notebook, benchmark, output, and authorization tools with names that can change. Discover the currently advertised tools and choose the narrowest tool that satisfies each step. Do not invent tool names.

For snapshot creation, the authoritative model catalog is the value returned inside the Kaggle benchmark runtime by:

```python
import kaggle_benchmarks as kbench
list(kbench.llms.keys())
```

A web page, cached list, prior run, README, or guessed provider lineup is not an acceptable substitute for `runtime-snapshot.json`.

## Evidence status

Before live model calls complete, describe UNISON as an empirical protocol.

After a valid runtime snapshot exists but before the full run completes, describe it as an empirical run in progress.

Only after sealed complete raw results and deterministic analysis exist may model-performance statements be described as empirical results.
