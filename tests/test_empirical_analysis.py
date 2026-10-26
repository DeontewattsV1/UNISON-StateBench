from pathlib import Path

from analysis.bootstrap import aggregate_empirical_records, scenario_cluster_bootstrap
from analysis.failure_topology import failure_topology
from benchmark.models import InvariantObservation, StructuredObservation
from benchmark.scoring import score_trial
from empirical.execute import _materialize
from empirical.freeze import FREEZE_SOURCE_REVISION
from empirical.plan import build_v01_plan
from empirical.records import EmpiricalRecord

ROOT = Path(__file__).resolve().parents[1]


def _perfect_records():
    plan = build_v01_plan(ROOT)
    records = []
    for item in plan.items:
        case, trial = _materialize(ROOT, item)
        expectation = trial.expectation
        observation = StructuredObservation(
            scenario_id=case.scenario_id,
            invariants=tuple(
                InvariantObservation(
                    id=invariant.id,
                    value=invariant.value,
                    epistemic_status=invariant.epistemic_status,
                    provenance=invariant.provenance,
                    authority_source=invariant.authority_source,
                )
                for invariant in expectation.invariants
            ),
            contradiction_detected=expectation.contradiction_expected,
            insufficient_evidence=expectation.insufficient_evidence_expected,
            decision=expectation.decision,
            authorized_actions=expectation.authorized_actions,
            explanation="deterministic perfect fixture",
        )
        score = score_trial(case, trial, observation)
        records.append(
            EmpiricalRecord(
                run_id="test-perfect",
                model_id="fixture/perfect",
                provider="fixture",
                source_revision=FREEZE_SOURCE_REVISION,
                plan_digest=plan.plan_digest,
                item=item,
                prompt_sha256="0" * 64,
                observation=observation,
                score=score,
                provider_metadata={"fixture": True},
                started_at="2026-10-01T00:00:00+00:00",
                completed_at="2026-10-01T00:00:01+00:00",
            )
        )
    return tuple(records)


def test_perfect_full_matrix_has_expected_eight_metric_vector():
    metrics = aggregate_empirical_records(_perfect_records())
    assert metrics.ipr.rate == 1.0
    assert metrics.rcr.rate == 1.0
    assert metrics.crr.rate == 1.0
    assert metrics.fhr.rate == 0.0
    assert metrics.cal.rate == 1.0
    assert metrics.plr.rate == 0.0
    assert metrics.air.rate == 0.0
    assert metrics.scr.rate == 0.0


def test_scenario_cluster_bootstrap_is_deterministic():
    records = _perfect_records()
    first = scenario_cluster_bootstrap(records, resamples=50, seed=1729)
    second = scenario_cluster_bootstrap(records, resamples=50, seed=1729)
    assert first == second
    assert first["ipr"].point == 1.0
    assert first["ipr"].low == 1.0
    assert first["ipr"].high == 1.0
    assert first["scr"].point == 0.0
    assert first["scr"].low == 0.0
    assert first["scr"].high == 0.0


def test_perfect_full_matrix_has_empty_failure_topology():
    topology = failure_topology(_perfect_records(), root=ROOT)
    assert topology["records"] == 162
    assert topology["successful_records"] == 162
    assert topology["failures"] == {}
    assert topology["invariant_component_failures"] == {}
    assert topology["collapse_kinds"] == {}
    assert topology["execution_errors"] == {}
    assert set(topology["u09_ipr_by_distance"]) == {"2048", "4096", "8192", "16384"}
    assert all(
        item["rate"] == 1.0
        for item in topology["u09_ipr_by_distance"].values()
    )
