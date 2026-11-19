"""
Model Router — The Performance Layer.

Decides whether a task can be resolved by policy rules, graph retrieval,
a compact reasoning model, or a larger synthesis model.
Enforces latency budgets, token budgets, and cost controls.

Design principle: small-model-first routing. Default to fast + cheap;
escalate to larger synthesis models only when necessary.

Capability level: ANI, Reactive, Deep Learning + Rules.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

_log = logging.getLogger("govcore.routing")


class RouteTarget(Enum):
    POLICY_RULES  = "policy_rules"    # Pure rule lookup — no model needed
    GRAPH_RETRIEVAL = "graph_retrieval" # Graph/ontology lookup
    SMALL_MODEL   = "small_model"     # Compact reasoning model (fast, cheap)
    LARGE_MODEL   = "large_model"     # Synthesis model (slower, higher cost)
    HUMAN_ONLY    = "human_only"      # Route directly to human — no AI synthesis


@dataclass
class RoutingDecision:
    target:          RouteTarget
    rationale:       str
    estimated_tokens: int
    estimated_latency_ms: float
    cost_tier:       str           # "zero" | "low" | "medium" | "high"
    fallback_target: Optional[RouteTarget] = None


@dataclass
class RoutingBudget:
    """Per-request resource constraints."""
    max_tokens:       int   = 4096
    max_latency_ms:   float = 5000.0
    max_cost_tier:    str   = "medium"  # "zero" | "low" | "medium" | "high"


class ModelRouter:
    """
    Routes incoming tasks to the most cost-effective model tier
    while staying within latency and token budgets.

    Routing priority:
      1. Policy rules lookup (zero tokens, near-zero latency)
      2. Graph/ontology retrieval (zero tokens)
      3. Small compact model (< 500ms, low cost)
      4. Large synthesis model (> 500ms, medium-high cost)
      5. Human-only (no model — for high-impact irreversible actions)
    """

    # Token estimates per route target
    TOKEN_ESTIMATES = {
        RouteTarget.POLICY_RULES:    0,
        RouteTarget.GRAPH_RETRIEVAL: 0,
        RouteTarget.SMALL_MODEL:     512,
        RouteTarget.LARGE_MODEL:     2048,
        RouteTarget.HUMAN_ONLY:      0,
    }

    LATENCY_ESTIMATES_MS = {
        RouteTarget.POLICY_RULES:    5.0,
        RouteTarget.GRAPH_RETRIEVAL: 25.0,
        RouteTarget.SMALL_MODEL:     350.0,
        RouteTarget.LARGE_MODEL:     2500.0,
        RouteTarget.HUMAN_ONLY:      0.0,
    }

    COST_TIERS = {
        RouteTarget.POLICY_RULES:    "zero",
        RouteTarget.GRAPH_RETRIEVAL: "zero",
        RouteTarget.SMALL_MODEL:     "low",
        RouteTarget.LARGE_MODEL:     "medium",
        RouteTarget.HUMAN_ONLY:      "zero",
    }

    def __init__(self, budget: Optional[RoutingBudget] = None):
        self.budget       = budget or RoutingBudget()
        self._route_log:  list = []
        self._stats       = {r: 0 for r in RouteTarget}
        _log.info("ModelRouter online.")

    def route(self, task: Dict) -> RoutingDecision:
        """
        Determine the optimal route for a task.

        Task keys:
          task_type (str): "policy_lookup" | "retrieval" | "analysis" | "synthesis" | "high_impact"
          complexity (str): "simple" | "moderate" | "complex"
          is_high_impact (bool): forces HUMAN_ONLY route
          requires_synthesis (bool): needs large model
          entity_count (int): number of entities to reason over
          fact_based (bool): can be answered from evidence alone
        """
        task_type    = task.get("task_type", "analysis")
        complexity   = task.get("complexity", "moderate")
        high_impact  = task.get("is_high_impact", False)
        needs_synth  = task.get("requires_synthesis", False)
        fact_based   = task.get("fact_based", False)
        entity_count = task.get("entity_count", 1)

        # Route 1: High-impact irreversible actions — human only
        if high_impact:
            return self._make_decision(
                RouteTarget.HUMAN_ONLY,
                "High-impact action flagged — routed directly to human operator.",
                fallback=None,
            )

        # Route 2: Pure policy or rule lookup
        if task_type == "policy_lookup" or (fact_based and complexity == "simple"):
            return self._make_decision(
                RouteTarget.POLICY_RULES,
                "Task is a policy rule lookup — no model inference needed.",
                fallback=RouteTarget.GRAPH_RETRIEVAL,
            )

        # Route 3: Graph / ontology retrieval
        if task_type == "retrieval" or (fact_based and entity_count <= 5):
            return self._make_decision(
                RouteTarget.GRAPH_RETRIEVAL,
                "Task is entity/relationship lookup — graph retrieval sufficient.",
                fallback=RouteTarget.SMALL_MODEL,
            )

        # Route 4: Small model — simple to moderate analysis
        if complexity in ("simple", "moderate") and not needs_synth:
            if self._within_budget(RouteTarget.SMALL_MODEL):
                return self._make_decision(
                    RouteTarget.SMALL_MODEL,
                    "Moderate complexity — small model meets task requirements within budget.",
                    fallback=RouteTarget.LARGE_MODEL,
                )

        # Route 5: Large synthesis model — complex or multi-modal
        if needs_synth or complexity == "complex" or entity_count > 10:
            if self._within_budget(RouteTarget.LARGE_MODEL):
                return self._make_decision(
                    RouteTarget.LARGE_MODEL,
                    "Complex synthesis task — large model required.",
                    fallback=RouteTarget.HUMAN_ONLY,
                )

        # Budget exceeded — escalate to human
        return self._make_decision(
            RouteTarget.HUMAN_ONLY,
            "Budget constraints exceeded — routing to human operator.",
            fallback=None,
        )

    def _within_budget(self, target: RouteTarget) -> bool:
        estimated_tokens  = self.TOKEN_ESTIMATES[target]
        estimated_latency = self.LATENCY_ESTIMATES_MS[target]
        cost_order        = ["zero", "low", "medium", "high"]

        if estimated_tokens > self.budget.max_tokens:
            return False
        if estimated_latency > self.budget.max_latency_ms:
            return False
        if cost_order.index(self.COST_TIERS[target]) > cost_order.index(self.budget.max_cost_tier):
            return False
        return True

    def _make_decision(
        self,
        target: RouteTarget,
        rationale: str,
        fallback: Optional[RouteTarget] = None,
    ) -> RoutingDecision:
        self._stats[target] += 1
        self._route_log.append({
            "target":   target.value,
            "rationale":rationale,
        })
        return RoutingDecision(
            target                = target,
            rationale             = rationale,
            estimated_tokens      = self.TOKEN_ESTIMATES[target],
            estimated_latency_ms  = self.LATENCY_ESTIMATES_MS[target],
            cost_tier             = self.COST_TIERS[target],
            fallback_target       = fallback,
        )

    def stats(self) -> Dict:
        total = sum(self._stats.values())
        return {
            "total_routed": total,
            "by_target": {k.value: v for k, v in self._stats.items()},
            "small_model_rate": f"{self._stats[RouteTarget.SMALL_MODEL] / max(total, 1):.1%}",
            "human_only_rate":  f"{self._stats[RouteTarget.HUMAN_ONLY] / max(total, 1):.1%}",
        }
