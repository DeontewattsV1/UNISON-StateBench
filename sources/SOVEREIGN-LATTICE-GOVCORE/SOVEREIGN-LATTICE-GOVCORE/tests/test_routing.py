"""Tests for Model Router."""
import pytest
from govcore.routing.router import ModelRouter, RouteTarget, RoutingBudget


def test_policy_lookup_routes_to_rules():
    r = ModelRouter()
    d = r.route({"task_type": "policy_lookup", "complexity": "simple"})
    assert d.target == RouteTarget.POLICY_RULES
    assert d.cost_tier == "zero"


def test_high_impact_routes_to_human():
    r = ModelRouter()
    d = r.route({"is_high_impact": True, "task_type": "network_isolation"})
    assert d.target == RouteTarget.HUMAN_ONLY


def test_complex_synthesis_routes_to_large_model():
    r = ModelRouter()
    d = r.route({"task_type": "synthesis", "complexity": "complex", "requires_synthesis": True})
    assert d.target == RouteTarget.LARGE_MODEL


def test_simple_analysis_routes_to_small_model():
    r = ModelRouter()
    d = r.route({"task_type": "analysis", "complexity": "simple", "fact_based": False})
    assert d.target == RouteTarget.SMALL_MODEL


def test_budget_exceeded_routes_to_human():
    tight_budget = RoutingBudget(max_tokens=100, max_latency_ms=10, max_cost_tier="zero")
    r = ModelRouter(budget=tight_budget)
    d = r.route({"task_type": "analysis", "complexity": "complex", "requires_synthesis": True})
    assert d.target == RouteTarget.HUMAN_ONLY


def test_stats_track_routes():
    r = ModelRouter()
    r.route({"task_type": "policy_lookup"})
    r.route({"is_high_impact": True})
    s = r.stats()
    assert s["total_routed"] == 2
