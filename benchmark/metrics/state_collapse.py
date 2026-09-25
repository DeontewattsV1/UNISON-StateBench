"""State Collapse Rate (SCR) aggregation helpers."""

from __future__ import annotations

from ..state_collapse import StateCollapseReport


def collapse_counts(report: StateCollapseReport) -> tuple[int, int]:
    return report.count, report.boundary_trials
