#!/usr/bin/env python3
"""Materialize the deterministic UNISON v0.1 empirical trial plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from empirical.plan import build_v01_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="experiments/v0.1/trial-matrix.jsonl")
    parser.add_argument("--manifest", default="experiments/v0.1/trial-matrix-manifest.json")
    args = parser.parse_args()

    plan = build_v01_plan(args.root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for item in plan.items:
            handle.write(
                json.dumps(item.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
                + "\n"
            )

    suites = Counter(item.suite.value for item in plan.items)
    manifest = {
        "schema": "unison.empirical.matrix-manifest.v1",
        "version": plan.version,
        "source_revision": plan.source_revision,
        "plan_digest": plan.plan_digest,
        "model_calls_per_model": plan.model_calls,
        "suite_calls": dict(sorted(suites.items())),
        "matrix_path": str(output),
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
