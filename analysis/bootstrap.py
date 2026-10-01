"""Deterministic scenario-cluster bootstrap for UNISON v0.1 empirical metrics."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from benchmark.scoring import BenchmarkMetrics, MetricRate, TrialScore, aggregate_scores
from empirical.records import EmpiricalRecord

METRIC_NAMES = ("ipr", "rcr", "crr", "fhr", "cal", "plr", "air", "scr")


@dataclass(frozen=True)
class ConfidenceInterval:
    point: float | None
    low: float | None
    high: float | None
    confidence: float
    method: str
    resamples: int


def _successful(records: tuple[EmpiricalRecord, ...] | list[EmpiricalRecord]):
    return tuple(item for item in records if item.succeeded)


def _cluster_id(record: EmpiricalRecord) -> str:
    if record.item.pair_id:
        return record.item.pair_id.split(":")[1]
    scenario = record.item.scenario_id
    return "S01" if scenario.startswith("S01_CF_") else scenario


def aggregate_empirical_records(records: tuple[EmpiricalRecord, ...] | list[EmpiricalRecord]) -> BenchmarkMetrics:
    """Aggregate eight metrics with RCR scoped only to representation-equivalence U01."""

    items = _successful(records)
    scores = tuple(item.score for item in items if item.score is not None)
    base = aggregate_scores(scores)
    u01_scores = tuple(
        item.score
        for item in items
        if item.item.suite.value == "U01" and item.score is not None
    )
    rcr = aggregate_scores(u01_scores).rcr if u01_scores else MetricRate.from_counts(0, 0)
    return base.model_copy(update={"rcr": rcr})


def _percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile of empty sample")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    weight = pos - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _rate(metrics: BenchmarkMetrics, name: str) -> float | None:
    return getattr(metrics, name).rate


def scenario_cluster_bootstrap(
    records: tuple[EmpiricalRecord, ...] | list[EmpiricalRecord],
    *,
    resamples: int = 10_000,
    seed: int = 1729,
    confidence: float = 0.95,
) -> dict[str, ConfidenceInterval]:
    """Percentile bootstrap resampling whole canonical scenarios with replacement.

    Whole-scenario resampling preserves dependence among representations, mutations,
    distance conditions, and the S01 U10 counterfactual pair.
    """

    if resamples <= 0:
        raise ValueError("resamples must be > 0")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")

    successful = _successful(records)
    if not successful:
        raise ValueError("No successful empirical records")

    grouped: dict[str, list[EmpiricalRecord]] = defaultdict(list)
    for record in successful:
        grouped[_cluster_id(record)].append(record)
    clusters = tuple(sorted(grouped))
    if len(clusters) < 2:
        raise ValueError("Scenario-cluster bootstrap requires at least two clusters")

    point = aggregate_empirical_records(successful)
    samples: dict[str, list[float]] = {name: [] for name in METRIC_NAMES}
    rng = random.Random(seed)

    for draw_index in range(resamples):
        sampled_records: list[EmpiricalRecord] = []
        for slot in range(len(clusters)):
            cluster = clusters[rng.randrange(len(clusters))]
            for record in grouped[cluster]:
                assert record.score is not None
                score = record.score.model_copy(
                    update={
                        "equivalence_group": (
                            f"{record.score.equivalence_group}:boot:{draw_index}:{slot}"
                        )
                    }
                )
                sampled_records.append(record.model_copy(update={"score": score}))
        metrics = aggregate_empirical_records(sampled_records)
        for name in METRIC_NAMES:
            value = _rate(metrics, name)
            if value is not None:
                samples[name].append(value)

    alpha = (1.0 - confidence) / 2.0
    intervals: dict[str, ConfidenceInterval] = {}
    for name in METRIC_NAMES:
        point_value = _rate(point, name)
        draws = samples[name]
        intervals[name] = ConfidenceInterval(
            point=point_value,
            low=_percentile(draws, alpha) if draws else None,
            high=_percentile(draws, 1.0 - alpha) if draws else None,
            confidence=confidence,
            method="scenario_cluster_percentile",
            resamples=resamples,
        )
    return intervals
