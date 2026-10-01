#!/usr/bin/env python3
"""Compute UNISON v0.1 metrics, confidence intervals, and failure topology."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from analysis.bootstrap import aggregate_empirical_records, scenario_cluster_bootstrap
from analysis.failure_topology import failure_topology
from empirical.records import load_jsonl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default="analysis-output")
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()

    by_model = defaultdict(list)
    for path in args.results:
        for record in load_jsonl(path):
            by_model[record.model_id].append(record)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = {"schema": "unison.empirical.analysis.v1", "models": {}}

    for model_id, records in sorted(by_model.items()):
        errors = [record for record in records if not record.succeeded]
        plan_ids = {record.item.plan_id for record in records}
        if len(records) != 162 or len(plan_ids) != 162 or errors:
            raise SystemExit(
                f"Model {model_id!r} is incomplete: records={len(records)}, "
                f"unique_plan_ids={len(plan_ids)}, errors={len(errors)}"
            )

        metrics = aggregate_empirical_records(records)
        cis = scenario_cluster_bootstrap(
            records, resamples=args.resamples, seed=args.seed
        )
        topology = failure_topology(records, root=args.root)

        model_summary = {
            "metrics": metrics.model_dump(mode="json"),
            "confidence_intervals": {
                name: {
                    "point": ci.point,
                    "low": ci.low,
                    "high": ci.high,
                    "confidence": ci.confidence,
                    "method": ci.method,
                    "resamples": ci.resamples,
                }
                for name, ci in cis.items()
            },
            "failure_topology": topology,
        }
        summary["models"][model_id] = model_summary

    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
