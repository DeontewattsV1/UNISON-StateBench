# %%
"""Kaggle notebook source for the UNISON-StateBench v0.1 empirical run.

Run the cells in order. The first phase snapshots the runtime. The operator then
selects exact keys from that snapshot. No model call occurs before the lineup is
content-addressed and written to disk.
"""

import json
import os
from pathlib import Path

import kaggle_benchmarks as kbench

from empirical.kaggle_runner import run_frozen_lineup
from empirical.lineup import freeze_lineup, snapshot_runtime, write_lineup, write_snapshot
from empirical.plan import build_v01_plan


# %%
ROOT = Path(".")
OUTPUT_DIR = Path("unison-v0.1-run")
RUN_ID = os.environ.get("UNISON_RUN_ID", "unison-v0.1-001")

plan = build_v01_plan(ROOT)
snapshot = snapshot_runtime(
    kbench,
    plan,
    runtime_metadata={"execution_surface": "kaggle_benchmarks"},
)
write_snapshot(OUTPUT_DIR / "runtime-snapshot.json", snapshot)

print(json.dumps({
    "source_revision": plan.source_revision,
    "plan_digest": plan.plan_digest,
    "calls_per_model": plan.model_calls,
    "available_model_keys": list(snapshot.available_model_keys),
    "snapshot_digest": snapshot.snapshot_digest,
}, indent=2, sort_keys=True))


# %%
# REQUIRED OPERATOR DECISION:
# Copy exact keys from the printed runtime snapshot. Do not guess model IDs.
# Example only; replace the empty tuple before proceeding.
SELECTED_MODEL_KEYS = tuple(
    key.strip()
    for key in os.environ.get("UNISON_MODEL_KEYS", "").split(",")
    if key.strip()
)

if not SELECTED_MODEL_KEYS:
    raise RuntimeError(
        "No model lineup selected. Set UNISON_MODEL_KEYS to exact comma-separated "
        "keys from runtime-snapshot.json, then rerun from this cell."
    )

lineup = freeze_lineup(
    snapshot,
    SELECTED_MODEL_KEYS,
    calls_per_model=plan.model_calls,
)
write_lineup(OUTPUT_DIR / "frozen-lineup.json", lineup)

print(json.dumps({
    "selected_model_keys": list(lineup.selected_model_keys),
    "model_count": lineup.model_count,
    "calls_per_model": lineup.calls_per_model,
    "total_model_calls": lineup.total_model_calls,
    "lineup_digest": lineup.lineup_digest,
}, indent=2, sort_keys=True))


# %%
# Model calls begin only after the exact lineup has been frozen above.
manifest = run_frozen_lineup(
    kbench,
    lineup,
    output_dir=OUTPUT_DIR / "raw-results",
    run_id=RUN_ID,
    root=ROOT,
)

print(json.dumps(manifest, indent=2, sort_keys=True))
