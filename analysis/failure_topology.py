"""Failure-topology summaries from preserved UNISON empirical observations."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from benchmark.metrics.invariant import score_invariant_preservation
from empirical.execute import _materialize
from empirical.freeze import verify_frozen_workspace
from empirical.records import EmpiricalRecord


def failure_topology(
    records: tuple[EmpiricalRecord, ...] | list[EmpiricalRecord],
    *,
    root: str | Path = ".",
) -> dict:
    root_path = Path(root).resolve()
    verify_frozen_workspace(root_path)

    counts = Counter()
    by_suite: dict[str, Counter] = defaultdict(Counter)
    by_scenario: dict[str, Counter] = defaultdict(Counter)
    by_representation: dict[str, Counter] = defaultdict(Counter)
    by_component = Counter()
    collapse_kinds = Counter()
    distance_counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    execution_errors = Counter()

    for record in records:
        item = record.item
        dimensions = (
            by_suite[item.suite.value],
            by_scenario[item.scenario_id],
            by_representation[item.representation.value],
        )

        if not record.succeeded:
            counts["execution_error"] += 1
            execution_errors[record.error or "unknown"] += 1
            for bucket in dimensions:
                bucket["execution_error"] += 1
            continue

        assert record.score is not None and record.observation is not None
        score = record.score

        def mark(name: str):
            counts[name] += 1
            for bucket in dimensions:
                bucket[name] += 1

        if score.invariant_preserved < score.invariant_tested:
            mark("invariant_failure")
            case, trial = _materialize(root_path, item)
            detail = score_invariant_preservation(trial.expectation, record.observation)
            for invariant in detail.details:
                if not invariant.value_preserved:
                    by_component["value"] += 1
                if not invariant.epistemic_preserved:
                    by_component["epistemic_status"] += 1
                if not invariant.provenance_preserved:
                    by_component["provenance"] += 1
                if not invariant.authority_preserved:
                    by_component["authority"] += 1

        if score.contradiction_recognized is False:
            mark("contradiction_miss")
        if score.false_harmonization is True:
            mark("false_harmonization")
        if score.correct_abstention is False:
            mark("abstention_failure")
        if score.principal_leakage is True:
            mark("principal_leakage")
        if score.authorization_risk is True:
            mark("authorization_risk")
        if score.collapse_report.count:
            mark("state_collapse")
            for collapse in score.collapse_report.collapses:
                collapse_kinds[collapse.kind.value] += 1

        if item.suite.value == "U09" and item.distance_units is not None:
            distance_counts[item.distance_units][0] += score.invariant_preserved
            distance_counts[item.distance_units][1] += score.invariant_tested

    return {
        "schema": "unison.empirical.failure-topology.v1",
        "records": len(records),
        "successful_records": sum(item.succeeded for item in records),
        "failures": dict(sorted(counts.items())),
        "invariant_component_failures": dict(sorted(by_component.items())),
        "collapse_kinds": dict(sorted(collapse_kinds.items())),
        "by_suite": {key: dict(sorted(value.items())) for key, value in sorted(by_suite.items())},
        "by_scenario": {key: dict(sorted(value.items())) for key, value in sorted(by_scenario.items())},
        "by_representation": {
            key: dict(sorted(value.items())) for key, value in sorted(by_representation.items())
        },
        "u09_ipr_by_distance": {
            str(distance): {
                "preserved": values[0],
                "tested": values[1],
                "rate": None if values[1] == 0 else values[0] / values[1],
            }
            for distance, values in sorted(distance_counts.items())
        },
        "execution_errors": dict(sorted(execution_errors.items())),
    }
