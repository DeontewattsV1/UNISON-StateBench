# Kaggle execution boundary

Kaggle's Community Benchmarks model catalog changes over time, so UNISON does not
hard-code guessed provider/model identifiers.

The publication path is deliberately two-phase:

1. run `kaggle/unison_v01_empirical_run.py` through its snapshot cell;
2. inspect the exact keys written to `runtime-snapshot.json`;
3. set `UNISON_MODEL_KEYS` to the exact selected keys;
4. rerun from the lineup-freeze cell;
5. confirm `frozen-lineup.json` and its digest;
6. only then execute the model calls.

The frozen lineup binds:

- frozen source revision;
- frozen 162-call plan digest;
- runtime availability snapshot digest;
- exact selected model keys and order;
- model count;
- calls per model;
- expected total calls.

Execution fails closed if any selected exact key disappears from the runtime. Raw
results also carry the lineup digest, preventing observations from being silently
combined across different model selections.

Do not publish model-performance claims from partial result files. The analysis
script requires exactly 162 unique successful plan IDs per model before computing
the eight metric families and confidence intervals.
